import logging
from app.schemas.sch_ai import JWType

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_jwks_decoded, get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.inv.i_tax import TaxDB
from app.schemas.sch_tax import TaxCreate, TaxOut
from app.service.ser_tax import create_or_update_tax, fetch_taxes

taxRou = APIRouter()
_log = logging.getLogger("app.http")


def _to_out(tax: TaxDB) -> TaxOut:
    return TaxOut(
        id=tax.id,
        tax_name=tax.tax_name,
        tax_rate=tax.tax_rate,
        tax_type=tax.tax_type,
        tax_note=tax.tax_note,
    )


@taxRou.get("/get_tax_list", response_model=list[TaxOut])
async def get_taxes(
    decoded: dict = Depends(get_jwks_decoded),
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    taxes = await fetch_taxes(zjwt, db)
    return [_to_out(tax) for tax in taxes]


@taxRou.post("/post_tax", response_model=TaxOut)
async def post_tax(
    payload: TaxCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    tax = await create_or_update_tax(zjwt, db, payload.model_dump(exclude_unset=True))
    return _to_out(tax)
