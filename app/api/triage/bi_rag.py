from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_ai import JWType
from app.schemas.sch_ai_rag_basic import QueryReq, QueryRes
from app.service.bi_rag_service import bi_rag_query_service


biRagRou = APIRouter()


@biRagRou.post("/rag_query", response_model=QueryRes)
async def bi_rag_query(
    payload: QueryReq,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    return await bi_rag_query_service(
        query=payload.query,
        top_k=payload.top_k,
        zjwt=zjwt,
        db=db,
    )
