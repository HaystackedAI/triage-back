import json
import logging
import asyncio
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.acc.ac_ledger import JournalEntryDB, JournalEntryLine
from app.schemas.sch_acc_je import TransactionOut, TransactionUpdateIn
from app.schemas.sch_ai import JWType
from app.service.acc.accounting import is_period_closed, yyyymm_from_date
from app.service.acc.ai_drafting import accounting_ai_model_name
from app.service.acc.inbox import DEFAULT_CURRENCY, add_transactions_from_inbox_message

rouTransaction = APIRouter()
logger = logging.getLogger("app.http")
JE_TABLE = JournalEntryDB.__table__
JE_LINE_TABLE = JournalEntryLine.__table__
_MONEY_QUANT = Decimal("0.01")
_STATUS_MAP = {
    "new": "draft",
    "mapped": "draft",
    "needs_review": "draft",
    "draft": "draft",
    "posted": "posted",
    "void": "void",
}


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _format_sse_comment(comment: str) -> str:
    return f": {comment}\n\n"


def _estimate_inbox_confidence(imported_count: int, duplicate_count: int) -> float:
    if imported_count > 0 and duplicate_count == 0:
        return 0.94
    if imported_count > 0:
        return 0.88
    if duplicate_count > 0:
        return 0.76
    return 0.70


class Add2InboxIn(BaseModel):
    message: str = Field(min_length=1)


class Add2InboxOut(BaseModel):
    message: str
    imported_count: int
    duplicate_count: int
    transactions: list[TransactionOut]


def _amount_to_cents(value: Decimal) -> int:
    return int((value.copy_abs().quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP) * 100).to_integral_value())


def _line_amount_updates(lines: list[Mapping[str, Any]], target_amount: Decimal) -> list[tuple[UUID, Decimal]]:
    target_cents = _amount_to_cents(target_amount)
    if target_cents <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry amount must be greater than zero")
    if target_cents < len(lines):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount is too small for the existing journal lines")

    old_total = sum((Decimal(line["amount"] or 0) for line in lines), Decimal("0"))
    if old_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing journal lines cannot be adjusted")

    remaining_cents = target_cents
    updates: list[tuple[UUID, Decimal]] = []
    for index, line in enumerate(lines):
        remaining_lines = len(lines) - index - 1
        if remaining_lines == 0:
            line_cents = remaining_cents
        else:
            proportional = Decimal(target_cents) * Decimal(line["amount"] or 0) / old_total
            line_cents = int(proportional.to_integral_value(rounding=ROUND_HALF_UP))
            line_cents = max(1, min(line_cents, remaining_cents - remaining_lines))

        updates.append((line["id"], (Decimal(line_cents) / Decimal(100)).quantize(_MONEY_QUANT)))
        remaining_cents -= line_cents
    return updates


async def _entry_transaction_amount(conn: AsyncConnection, entry: Mapping[str, Any]) -> Decimal:
    if entry["b_decimal"] is not None:
        return Decimal(entry["b_decimal"])

    lines = list((
        await conn.execute(
            select(JE_LINE_TABLE)
            .where(JE_LINE_TABLE.c.journal_entry_id == entry["id"])
            .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
        )
    ).mappings().all())
    debit_total = sum((Decimal(line["amount"] or 0) for line in lines if line["line_type"] == "Debit"), Decimal("0"))
    credit_total = sum((Decimal(line["amount"] or 0) for line in lines if line["line_type"] == "Credit"), Decimal("0"))
    return max(debit_total, credit_total)


async def _entry_to_transaction_out(conn: AsyncConnection, entry: Mapping[str, Any]) -> TransactionOut:
    extra = entry["extra"] or {}
    return TransactionOut(
        id=entry["id"],
        txn_date=entry["entry_date"],
        description=entry["memo"] or entry["description"] or "",
        amount=await _entry_transaction_amount(conn, entry),
        currency=entry["locale"] or str(extra.get("currency") or DEFAULT_CURRENCY),
        status=entry["entry_status"] or "draft",
        source_file_name=extra.get("source_file_name") if isinstance(extra, dict) else None,
        created_at=entry["created_at"],
        journal_id=entry["id"],
        is_deleted=entry["is_deleted"],
    )


async def _sync_entry_for_transaction_update(
    conn: AsyncConnection,
    entry: Mapping[str, Any],
    updates: dict[str, Any],
) -> None:
    if "amount" in updates:
        lines = list((
            await conn.execute(
                select(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.journal_entry_id == entry["id"])
                .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all())
        if not lines:
            return

        debit_lines = [line for line in lines if line["line_type"] == "Debit"]
        credit_lines = [line for line in lines if line["line_type"] == "Credit"]
        if not debit_lines or not credit_lines:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry must have debit and credit lines")

        target_amount = Decimal(entry["b_decimal"] or 0)
        for line_id, amount in [*_line_amount_updates(debit_lines, target_amount), *_line_amount_updates(credit_lines, target_amount)]:
            await conn.execute(
                update(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.id == line_id)
                .values(amount=amount)
            )


async def _get_entry_or_404(conn: AsyncConnection, transaction_id: UUID) -> Mapping[str, Any]:
    entry = (
        await conn.execute(
            select(JE_TABLE)
            .where(JE_TABLE.c.id == transaction_id)
            .where(JE_TABLE.c.is_deleted.is_not(True))
        )
    ).mappings().one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return entry


@rouTransaction.get("/get_transaction_list", response_model=list[TransactionOut])
async def list_transactions(
    status_filter: str | None = Query(default=None, alias="status"),
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 100,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> list[TransactionOut]:
    stmt = select(JE_TABLE).order_by(JE_TABLE.c.created_at.desc())
    stmt = stmt.where(JE_TABLE.c.is_deleted.is_not(True))
    if status_filter:
        mapped_status = _STATUS_MAP.get(status_filter.lower(), status_filter)
        stmt = stmt.where(JE_TABLE.c.entry_status == mapped_status)
    if from_date:
        stmt = stmt.where(JE_TABLE.c.entry_date >= from_date)
    if to_date:
        stmt = stmt.where(JE_TABLE.c.entry_date <= to_date)
    stmt = stmt.limit(max(1, min(500, limit)))
    entries = list((await conn.execute(stmt)).mappings().all())
    return [await _entry_to_transaction_out(conn, entry) for entry in entries]


@rouTransaction.post("/add2inbox", response_model=Add2InboxOut, status_code=status.HTTP_201_CREATED)
async def add2inbox(
    payload: Add2InboxIn,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> Add2InboxOut:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")
    result = await add_transactions_from_inbox_message(conn=conn, zjwt=zjwt, message=message)

    return Add2InboxOut(
        message=result.message,
        imported_count=result.imported_count,
        duplicate_count=result.duplicate_count,
        transactions=[await _entry_to_transaction_out(conn, entry) for entry in result.transactions],
    )


@rouTransaction.post("/add2inbox_stream")
async def add2inbox_stream(
    payload: Add2InboxIn,
    request: Request,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> StreamingResponse:
    message = payload.message.strip()
    # Direct OpenAI switch notes live beside the active client in ai_drafting.py.
    model = accounting_ai_model_name()

    async def event_stream():
        yield _format_sse("status", {"status": "start", "meta": {"message": message, "model": model}})
        await asyncio.sleep(0.05)

        try:
            if not message:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")

            yield _format_sse("status", {"status": "validating_note", "meta": {"characters": len(message)}})
            await asyncio.sleep(0.05)
            yield _format_sse("status", {"status": "calling_ai_model", "meta": {"model": model}})
            await asyncio.sleep(0.05)
            yield _format_sse("status", {"status": "interpreting_transaction", "meta": {"model": model}})
            await asyncio.sleep(0.05)
            logger.info("add2inbox_stream calling AI/import/generate pipeline model=%s", model)
            result = await add_transactions_from_inbox_message(conn=conn, zjwt=zjwt, message=message)
            logger.info(
                "add2inbox_stream pipeline finished imported=%s duplicate=%s",
                result.imported_count,
                result.duplicate_count,
            )

            if await request.is_disconnected():
                return

            transactions_meta = []
            transactions_out = []
            for entry in result.transactions:
                transaction = await _entry_to_transaction_out(conn, entry)
                transactions_out.append(transaction)
                transactions_meta.append(
                    {
                        "txn_date": transaction.txn_date.isoformat(),
                        "description": transaction.description,
                        "amount": str(transaction.amount),
                        "currency": transaction.currency,
                    }
                )

            confidence_score = _estimate_inbox_confidence(result.imported_count, result.duplicate_count)
            yield _format_sse("status", {
                "status": "understanding_transaction",
                "meta": {
                    "confidence_score": confidence_score,
                    "transactions": transactions_meta,
                },
            })
            await asyncio.sleep(0.05)
            yield _format_sse("status", {
                "status": "transactions_found",
                "meta": {"count": len(result.transactions) + result.duplicate_count},
            })
            await asyncio.sleep(0.05)
            yield _format_sse("status", {"status": "saving_inbox", "meta": {}})
            await asyncio.sleep(0.05)
            yield _format_sse("status", {
                "status": "import_summary",
                "meta": {
                    "imported_count": result.imported_count,
                    "duplicate_count": result.duplicate_count,
                },
            })
            await asyncio.sleep(0.05)

            response = Add2InboxOut(
                message=result.message,
                imported_count=result.imported_count,
                duplicate_count=result.duplicate_count,
                transactions=transactions_out,
            )
            yield _format_sse("final", {
                "response": {
                    **response.model_dump(mode="json"),
                    "model": model,
                    "confidence_score": confidence_score,
                }
            })
        except HTTPException as exc:
            yield _format_sse("error", {"message": str(exc.detail)})
        except Exception as exc:
            logger.exception("add2inbox_stream failed", exc_info=exc)
            yield _format_sse("error", {"message": "internal_error"})
        finally:
            if not await request.is_disconnected():
                yield _format_sse_comment(f"done {datetime.now(timezone.utc).isoformat()}")

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=headers,
        status_code=status.HTTP_201_CREATED,
    )


@rouTransaction.get("/get_one_transaction/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: UUID,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> TransactionOut:
    entry = await _get_entry_or_404(conn, transaction_id)
    return await _entry_to_transaction_out(conn, entry)


@rouTransaction.patch("/update_transaction/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdateIn,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> TransactionOut:
    entry = await _get_entry_or_404(conn, transaction_id)

    updates = payload.model_dump(exclude_unset=True)
    values: dict[str, Any] = {}
    if "status" in updates:
        mapped_status = _STATUS_MAP.get(str(updates["status"]).lower())
        if mapped_status is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction status")
        values["entry_status"] = mapped_status
    if "txn_date" in updates:
        period = yyyymm_from_date(updates["txn_date"])
        if await is_period_closed(conn, period):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Period is closed")
        values["entry_date"] = updates["txn_date"]
        values["period_yyyymm"] = period
    if "description" in updates:
        values["memo"] = updates["description"]
        values["description"] = updates["description"]
    if "amount" in updates:
        values["b_decimal"] = updates["amount"]

    if values:
        entry = (
            await conn.execute(
                update(JE_TABLE)
                .where(JE_TABLE.c.id == entry["id"])
                .values(**values)
                .returning(*JE_TABLE.c)
            )
        ).mappings().one()
    await _sync_entry_for_transaction_update(conn, entry, updates)
    return await _entry_to_transaction_out(conn, entry)


@rouTransaction.post("/void_transaction/{transaction_id}", response_model=TransactionOut)
async def void_transaction(
    transaction_id: UUID,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> TransactionOut:
    entry = await _get_entry_or_404(conn, transaction_id)
    entry = (
        await conn.execute(
            update(JE_TABLE)
            .where(JE_TABLE.c.id == entry["id"])
            .values(entry_status="void", is_deleted=True)
            .returning(*JE_TABLE.c)
        )
    ).mappings().one()
    await conn.execute(
        update(JE_LINE_TABLE)
        .where(JE_LINE_TABLE.c.journal_entry_id == entry["id"])
        .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
        .values(is_deleted=True)
    )
    return await _entry_to_transaction_out(conn, entry)
