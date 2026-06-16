from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.t4.m_payroll_history import PayrollHistoryDB
from app.schemas.sch_ai import JWType
from app.schemas.sch_payroll_history import (
    PayrollHistoryDetailOut,
    PayrollHistoryOut,
    PayrollHistorySummaryOut,
)
from app.service.ser_payroll_history import (
    fetch_payroll_history,
    fetch_payroll_history_detail,
    fetch_payroll_history_summary_list,
)

historyRou = APIRouter()


def _to_db_dict(payroll_history: PayrollHistoryDB) -> dict[str, Any]:
    return {
        column.name: getattr(payroll_history, column.name)
        for column in payroll_history.__table__.columns
    }


@historyRou.get("/get_payroll_history_list", response_model=list[PayrollHistoryOut])
async def get_payroll_history_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    sbu_client_id = zjwt.zcid
    if not sbu_client_id:return []
    history_rows = await fetch_payroll_history(sbu_client_id, db)
    return [PayrollHistoryOut(**_to_db_dict(history)) for history in history_rows]


@historyRou.get("/get_payroll_history_summary_list", response_model=list[PayrollHistorySummaryOut])
async def get_payroll_history_summary_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    sbu_client_id = zjwt.zcid
    if not sbu_client_id:return []
    return await fetch_payroll_history_summary_list(sbu_client_id, db)


@historyRou.get("/get_payroll_history_detail", response_model=PayrollHistoryDetailOut)
async def get_payroll_history_detail(
    id: str | None = Query(default=None),
    period_key: str | None = Query(default=None),
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    history_id: UUID | None = None
    if id and not period_key:
        try:
            history_id = UUID(id)
        except ValueError:
            period_key = id

    sbu_client_id = zjwt.zcid
    if not sbu_client_id:return None
    return await fetch_payroll_history_detail(
        sbu_client_id,
        db,
        period_key=period_key,
        history_id=history_id,
    )
