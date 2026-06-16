from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.t4.m_payroll_schedule import PayrollScheduleDB
from app.schemas.sch_ai import JWType
from app.schemas.sch_payroll_schedule import PayrollScheduleOut, PayrollScheduleUpsert
from app.service.ser_payroll_schedule import create_or_update_payroll_schedule, fetch_payroll_schedules

scheduleRou = APIRouter()


def _to_db_dict(payroll_schedule: PayrollScheduleDB) -> dict[str, Any]:
    return {
        column.name: getattr(payroll_schedule, column.name)
        for column in payroll_schedule.__table__.columns
    }


@scheduleRou.get("/get_payroll_schedule_list", response_model=list[PayrollScheduleOut])
async def get_payroll_schedule_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    sbu_client_id = zjwt.zcid
    if not sbu_client_id:return []
    schedules = await fetch_payroll_schedules(sbu_client_id, db)
    return [PayrollScheduleOut(**_to_db_dict(schedule)) for schedule in schedules]


@scheduleRou.post("/post_payroll_schedule", response_model=PayrollScheduleOut)
async def post_payroll_schedule(
    payload: PayrollScheduleUpsert,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    schedule = await create_or_update_payroll_schedule(zjwt, db, payload)
    return PayrollScheduleOut(**_to_db_dict(schedule))
