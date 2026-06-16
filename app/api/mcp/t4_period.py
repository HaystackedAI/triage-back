from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.t4.m_payroll_period import PayrollPeriodDB
from app.schemas.sch_ai import JWType
from app.schemas.sch_payroll_period import PayrollPeriodOut
from app.service.ser_payroll_period import fetch_payroll_periods

periodRou = APIRouter()


def _to_db_dict(payroll_period: PayrollPeriodDB) -> dict[str, Any]:
    return {
        column.name: getattr(payroll_period, column.name)
        for column in payroll_period.__table__.columns
    }


@periodRou.get("/get_payroll_period_list", response_model=list[PayrollPeriodOut])
async def get_payroll_period_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    sbu_client_id = zjwt.zcid
    if not sbu_client_id:return []
    periods = await fetch_payroll_periods(sbu_client_id, db)
    return [PayrollPeriodOut(**_to_db_dict(period)) for period in periods]
