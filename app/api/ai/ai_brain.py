from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.langgraph.sse.lgstream import build_langgraph_sse_response
from app.schemas.sch_ai import JWType
from app.schemas.sch_ai_rag_basic import RagRerankAnswerResponse
from app.schemas.sch_ai_feedback import FeedbackCreateRequest, FeedbackCreateResponse
from app.schemas.sch_ai_router import RouterQueryRequest
from app.service.ser_ai_feedback import log_feedback_event
from app.service.ser_ai_router import route_and_answer as route_and_answer_service

brainRou = APIRouter()
logger = logging.getLogger("app.http")

@brainRou.post("/python", response_model=RagRerankAnswerResponse)
async def route_answer(
    payload: RouterQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    return await route_and_answer_service(payload, zjwt, db)


@brainRou.post("/langgraph", response_model=RagRerankAnswerResponse)
async def route_answer_langgraph(
    payload: RouterQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    try:
        from app.langgraph.agent2 import route_and_answer as route_langgraph
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LangGraph not available: {exc}") from exc

    return await route_langgraph(payload, zjwt, db)


@brainRou.post("/lgstream")
async def route_answer_langgraph_stream(
    payload: RouterQueryRequest,
    request: Request,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    try:
        from app.langgraph.agent2 import route_and_answer as route_langgraph
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LangGraph not available: {exc}") from exc

    return build_langgraph_sse_response(
        payload=payload,
        request=request,
        zjwt=zjwt,
        db=db,
        route_langgraph=route_langgraph,
        logger=logger,
    )

