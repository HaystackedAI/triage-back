from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_ai import JWType
from app.service.acc.accounting import balance_sheet, export_tax_package_zip, income_statement, ledger_rows, trial_balance

router = APIRouter(tags=["reports"])


@router.get("/ledger/general")
async def get_general_ledger(
    account_id: UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> dict:
    rows = []
    running = {}
    for row in await ledger_rows(conn, from_date=from_date, to_date=to_date, account_id=account_id):
        (
            journal_entry_id,
            entry_date,
            memo,
            line_id,
            acct_id,
            coa_code,
            coa_name,
            parent_id,
            coa_status,
            coa_level,
            normal_balance,
            _is_posting,
            line_type,
            amount,
        ) = row
        current = running.get(acct_id, 0)
        delta = float(amount) if line_type == "Debit" else -float(amount)
        current += delta
        running[acct_id] = current
        rows.append(
            {
                "id": line_id,
                "journal_entry_line_id": line_id,
                "journal_entry_id": journal_entry_id,
                "entry_date": entry_date,
                "memo": memo,
                "account_id": acct_id,
                "coa_code": coa_code,
                "coa_name": coa_name,
                "parent_id": parent_id,
                "coa_status": coa_status,
                "coa_level": coa_level,
                "normal_balance": normal_balance,
                "line_type": line_type,
                "amount": amount,
                "running_balance": current,
            }
        )
    return {"rows": rows}


@router.get("/reports/trial-balance")
async def get_trial_balance(
    period_yyyymm: int | None = Query(default=None),
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> dict:
    from_date = to_date = None
    if period_yyyymm:
        year = period_yyyymm // 100
        month = period_yyyymm % 100
        from_date = date(year, month, 1)
        to_date = date(year, month, 28)
        while True:
            try:
                to_date = to_date.replace(day=to_date.day + 1)
            except ValueError:
                break
    return {"rows": await trial_balance(conn, from_date=from_date, to_date=to_date)}


@router.get("/reports/balance-sheet")
async def get_balance_sheet(
    as_of: date,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> dict:
    return await balance_sheet(conn, as_of)


@router.get("/reports/income-statement")
async def get_income_statement(
    from_date: date,
    to_date: date,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> dict:
    return await income_statement(conn, from_date, to_date)


@router.get("/reports/export-tax-package")
async def get_export_tax_package(
    period_yyyymm: int,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> StreamingResponse:
    data = await export_tax_package_zip(conn, period_yyyymm)
    return StreamingResponse(iter([data]), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=tax_package_{period_yyyymm}.zip"})
