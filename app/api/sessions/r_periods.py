from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.acc.ac_ledger import PeriodCloseDB
from app.schemas.sch_ai import JWType

router = APIRouter(prefix="/periods", tags=["periods"])
PERIOD_CLOSE_TABLE = PeriodCloseDB.__table__


@router.post("/{period_yyyymm}/close")
async def close_period(
    period_yyyymm: int,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> dict:
    row = (
        await conn.execute(
            select(PERIOD_CLOSE_TABLE)
            .where(PERIOD_CLOSE_TABLE.c.period_yyyymm == period_yyyymm)
        )
    ).mappings().one_or_none()
    if row and row["is_closed"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Period already closed")
    values = {
        "is_closed": True,
        "closed_at": datetime.now(timezone.utc),
        "closed_by": zjwt.zuid,
    }
    if not row:
        await conn.execute(
            insert(PERIOD_CLOSE_TABLE).values(
                ten_id=zjwt.ztid,
                biz_id=zjwt.zbid,
                usr_id=zjwt.zuid,
                created_by=zjwt.zuid,
                period_yyyymm=period_yyyymm,
                **values,
            )
        )
    else:
        await conn.execute(
            update(PERIOD_CLOSE_TABLE)
            .where(PERIOD_CLOSE_TABLE.c.id == row["id"])
            .values(**values)
        )
    return {"period_yyyymm": period_yyyymm, "is_closed": True}


@router.post("/{period_yyyymm}/reopen")
async def reopen_period(
    period_yyyymm: int,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> dict:
    row = (
        await conn.execute(
            select(PERIOD_CLOSE_TABLE)
            .where(PERIOD_CLOSE_TABLE.c.period_yyyymm == period_yyyymm)
        )
    ).mappings().one_or_none()
    values = {"is_closed": False, "closed_at": None, "closed_by": None}
    if not row:
        await conn.execute(
            insert(PERIOD_CLOSE_TABLE).values(
                ten_id=zjwt.ztid,
                biz_id=zjwt.zbid,
                usr_id=zjwt.zuid,
                created_by=zjwt.zuid,
                period_yyyymm=period_yyyymm,
                **values,
            )
        )
    else:
        await conn.execute(
            update(PERIOD_CLOSE_TABLE)
            .where(PERIOD_CLOSE_TABLE.c.id == row["id"])
            .values(**values)
        )
    return {"period_yyyymm": period_yyyymm, "is_closed": False}
