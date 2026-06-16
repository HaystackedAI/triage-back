from app.schemas.sch_ai import JWType

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.inv.i_payment_method import PaymentMethodDB
from app.schemas.sch_payment_method import PaymentMethodCreate, PaymentMethodOut
from app.service.ser_payment_method import (
    create_or_update_payment_method,
    fetch_payment_methods,
)

pmRou = APIRouter()


def _to_out(method: PaymentMethodDB) -> PaymentMethodOut:
    return PaymentMethodOut(
        id=method.id,
        pm_name=method.pm_name,
        pm_note=method.pm_note,
    )


@pmRou.get("/get_pm_list", response_model=list[PaymentMethodOut])
async def get_payment_methods(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    methods = await fetch_payment_methods(zjwt, db)
    return [_to_out(method) for method in methods]


@pmRou.post("/post_pm", response_model=PaymentMethodOut)
async def post_payment_method(
    payload: PaymentMethodCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    method = await create_or_update_payment_method(zjwt, db, payload.model_dump(exclude_unset=True))
    return _to_out(method)
