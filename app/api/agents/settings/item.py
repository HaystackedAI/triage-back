from app.schemas.sch_ai import JWType

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.inv.i_tem import ItemDB
from app.schemas.sch_item import ItemCreate, ItemOut
from app.service.ser_item import create_or_update_item, fetch_items

itemRou = APIRouter()


def _to_out(item: ItemDB) -> ItemOut:
    return ItemOut(
        id=item.id,
        item_number=item.item_number,
        item_name=item.item_name,
        item_rate=item.item_rate,
        item_unit_of_measure=item.item_unit_of_measure,
        item_unit=item.item_unit,
        item_sku=item.item_sku,
        item_description=item.item_description,
        item_quantity=item.item_quantity,
        item_note=item.item_note,
        item_amount=item.item_amount,
    )


@itemRou.get("/get_item_list", response_model=list[ItemOut])
async def get_items(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    items = await fetch_items(zjwt, db)
    return [_to_out(item) for item in items]


@itemRou.post("/post_item", response_model=ItemOut)
async def post_item(
    payload: ItemCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    item = await create_or_update_item(zjwt, db, payload.model_dump(exclude_unset=True))
    return _to_out(item)
