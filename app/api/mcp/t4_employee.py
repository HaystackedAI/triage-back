from typing import Any
from uuid import UUID
from app.schemas.sch_ai import JWType
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.db_async import get_db_admin
from app.db.models.t4.m_employee import EmployeeDB
from app.schemas.sch_employee import EmployeeCreate, EmployeeOut
from app.service.ser_employee import create_or_update_employee, fetch_employees

employeeRou = APIRouter()


def _to_db_dict(employee: EmployeeDB) -> dict[str, Any]:
    return {column.name: getattr(employee, column.name) for column in employee.__table__.columns}


@employeeRou.get("/get_employee_list", response_model=list[EmployeeOut])
async def get_employee_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_db_admin),
):
    sbu_client_id = zjwt.zcid
    if not sbu_client_id:raise ValueError("sbu_client_id is missing in the JWT")
    employees = await fetch_employees(sbu_client_id, db)
    print(f"Fetched employees: {employees}")
    return [EmployeeOut(**_to_db_dict(employee)) for employee in employees]


@employeeRou.post("/post_employee", response_model=EmployeeOut)
async def post_employee(
    payload: EmployeeCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_db_admin),
):
    # zuid = UUID(zjwt)
    employee = await create_or_update_employee(zjwt, db, payload.model_dump(exclude_unset=True))
    return EmployeeOut(**_to_db_dict(employee))
