from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_acc_je import JournalEntryOut, JournalEntryUpdateIn, JournalGenerateIn
from app.schemas.sch_ai import JWType
from app.service.acc.journal_entries import (
    isdelete_journal_entry,
    generate_entry_for_transaction,
    get_journal_entry,
    list_journal_entries,
    reverse_journal_entry,
    update_journal_entry,
)

router = APIRouter(prefix="/je", tags=["journal-entries"])


@router.post("/generate", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
async def generate_entry(
    payload: JournalGenerateIn,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> JournalEntryOut:
    return await generate_entry_for_transaction(
        conn=conn,
        zjwt=zjwt,
        transaction_id=payload.transaction_id,
        force=payload.force,
    )


@router.get("/getlist", response_model=list[JournalEntryOut])
async def list_entries(
    period_yyyymm: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> list[JournalEntryOut]:
    return await list_journal_entries(conn=conn, period_yyyymm=period_yyyymm, limit=limit)


@router.get("/getone/{journal_entry_id}", response_model=JournalEntryOut)
async def get_entry(
    journal_entry_id: UUID,
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> JournalEntryOut:
    return await get_journal_entry(conn=conn, journal_entry_id=journal_entry_id)


@router.patch("/{journal_entry_id}", response_model=JournalEntryOut)
async def update_entry(
    journal_entry_id: UUID,
    payload: JournalEntryUpdateIn,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> JournalEntryOut:
    return await update_journal_entry(
        conn=conn,
        zjwt=zjwt,
        journal_entry_id=journal_entry_id,
        payload=payload,
    )


@router.delete("/{journal_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    journal_entry_id: UUID,
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> None:
    await isdelete_journal_entry(conn=conn, journal_entry_id=journal_entry_id)


@router.post("/{journal_entry_id}/reverse", response_model=JournalEntryOut)
async def reverse_entry(
    journal_entry_id: UUID,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> JournalEntryOut:
    return await reverse_journal_entry(conn=conn, zjwt=zjwt, journal_entry_id=journal_entry_id)
