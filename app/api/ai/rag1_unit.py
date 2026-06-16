from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_ai import JWType, RagRetrieveRes
from app.schemas.sch_ai_rag_basic import (QueryReq, QueryRes)
from app.service.ser_ai_embedding import (rag_query,retrieve_hybrid_candidates,retrieve_keyword_candidates,retrieve_vector_candidates,)

ragUnitRou = APIRouter()
logger = logging.getLogger("app.http")


@ragUnitRou.post("/cosine", response_model=QueryRes)
async def rag_query_cosine(
    payload: QueryReq,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    return await rag_query(payload, zjwt, db)


@ragUnitRou.post("/vector", response_model=RagRetrieveRes)
async def rag_query_vector(
    payload: QueryReq,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    results = await retrieve_vector_candidates(payload, zjwt, db)
    return {
        "query": payload.query,
        "top_k": payload.top_k,
        "mode": "vector",
        "results": results,
    }


@ragUnitRou.post("/keyword", response_model=RagRetrieveRes)
async def rag_query_keyword(
    payload: QueryReq,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    results = await retrieve_keyword_candidates(payload, zjwt, db)
    return {
        "query": payload.query,
        "top_k": payload.top_k,
        "mode": "keyword",
        "results": results,
    }


@ragUnitRou.post("/hybrid", response_model=RagRetrieveRes)
async def rag_query_hybrid(
    payload: QueryReq,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    results = await retrieve_hybrid_candidates(payload, zjwt, db)
    return {
        "query": payload.query,
        "top_k": payload.top_k,
        "mode": "hybrid",
        "results": results,
    }

