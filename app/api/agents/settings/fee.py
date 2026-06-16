from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.inv.i_fee import FeeDB
from app.schemas.sch_ai import JWType
from app.schemas.sch_fee import FeeCreate, FeeOut
from app.service.ser_fee import create_or_update_fee, fetch_fees

feeRou = APIRouter()


def _to_out(fee: FeeDB) -> FeeOut:
    return FeeOut(
        id=fee.id,
        fee_name=fee.fee_name,
        fee_amount=fee.fee_amount,
        fee_note=fee.fee_note,
    )


@feeRou.get("/get_fee_list", response_model=list[FeeOut])
async def get_fees(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    # zuid = UUID(zjwt)
    fees = await fetch_fees(zjwt, db)
    return [_to_out(fee) for fee in fees]


@feeRou.post("/create_fee", response_model=FeeOut)
async def post_fee(
    payload: FeeCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    fee = await create_or_update_fee(zjwt, db, payload.model_dump(exclude_unset=True))
    return _to_out(fee)
