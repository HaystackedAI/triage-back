from __future__ import annotations

import asyncio, json, logging, time
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.brain import TOP_K_MODEL, decide_top_k
from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_ai import JWType, RagRetrieveRes
from app.schemas.sch_ai_rag_basic import (
    RagAnswerResponse,
    QueryReq,
    RagRerankAnswerResponse,
)
from app.schemas.sch_ai_feedback import FeedbackCreateRequest, FeedbackCreateResponse
from app.service.ser_ai_embedding import (minimize_evidence_for_llm,rag_answer,rag_rerank,)
from app.service.ser_ai_feedback import log_feedback_event
from app.service.ser_ai_guardrail import log_rag_guardrail

ragLLMRou = APIRouter()
logger = logging.getLogger("app.http")

def _format_sse(event: str, data: dict) -> str: return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
def _format_sse_comment(comment: str) -> str: return f": {comment}\n\n"


@ragLLMRou.post("/llm_answer", response_model=RagAnswerResponse)
async def rag2_answer(
    payload: QueryReq,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    start = time.perf_counter()
    response = await rag_answer(payload, zjwt, db)
    latency_ms = (time.perf_counter() - start) * 1000

    guardrail_meta = response.pop("_guardrail", None)
    try:
        guardrail_evidence = minimize_evidence_for_llm(response.get("evidence") or [], payload.query)
        await log_rag_guardrail(
            db,
            ten_id=zjwt.ztid,
            biz_id=zjwt.zbid,
            user_id=zjwt.zuid,
            route="rag_answer",
            question=payload.query,
            answer=response.get("answer") or "",
            evidence=guardrail_evidence,
            model=response.get("model"),
            latency_ms=latency_ms,
            guardrail_meta=guardrail_meta,
        )
    except Exception:
        pass

    return response



@ragLLMRou.post("/rerank", response_model=RagRerankAnswerResponse)
async def rag3_answer_rerank(
    payload: QueryReq,
    retrieval_mode: Literal["vector", "keyword", "hybrid"] = "hybrid",
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    start = time.perf_counter()
    response = await rag_rerank(payload, zjwt, db=db, retrieval_mode=retrieval_mode)
    latency_ms = (time.perf_counter() - start) * 1000

    guardrail_meta = response.pop("_guardrail", None)
    try:
        guardrail_evidence = minimize_evidence_for_llm(response.get("evidence") or [], payload.query)
        await log_rag_guardrail(
            db,
            ten_id=zjwt.ztid,
            biz_id=zjwt.zbid,
            user_id=zjwt.zuid,
            route="rag_answer_rerank",
            question=payload.query,
            answer=response.get("answer") or "",
            evidence=guardrail_evidence,
            model=response.get("model"),
            latency_ms=latency_ms,
            guardrail_meta=guardrail_meta,
        )
    except Exception:
        pass

    return response


@ragLLMRou.post("/rerank_stream")
async def rag_answer_rerank_stream(
    payload: QueryReq,
    request: Request,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()
    keepalive_seconds = 15.0
    start = time.perf_counter()

    async def status_cb(status: str, meta: dict | None = None) -> None:
        await queue.put(("status", {"status": status, "meta": meta or {}}))

    async def runner() -> None:
        try:
            decided_top_k = payload.top_k
            top_k_reasoning: list[str] = []
            top_k_rationale = ""
            try:
                decided_top_k, top_k_rationale, top_k_reasoning = await decide_top_k(
                    payload.query,
                    default_top_k=payload.top_k,
                )
                await status_cb(
                    "rag_top_k",
                    {"top_k": decided_top_k, "rationale": top_k_rationale, "model": TOP_K_MODEL},
                )
            except Exception:
                await status_cb(
                    "rag_top_k_fallback",
                    {"top_k": decided_top_k, "reason": "top_k_decision_failed"},
                )

            decided_payload = QueryReq(query=payload.query, top_k=decided_top_k)
            result = await rag_rerank(decided_payload, zjwt, db, status_cb=status_cb)
            if isinstance(result, dict):
                result["top_k"] = decided_top_k
                if top_k_reasoning:
                    result["model_reasoning_summary"] = list(top_k_reasoning) + list(
                        result.get("model_reasoning_summary") or []
                    )
            latency_ms = (time.perf_counter() - start) * 1000
            guardrail_meta = result.pop("_guardrail", None)
            try:
                guardrail_evidence = minimize_evidence_for_llm(result.get("evidence") or [], payload.query)
                await log_rag_guardrail(
                    db,
                    ten_id=zjwt.ztid,
                    biz_id=zjwt.zbid,
                    user_id=zjwt.zuid,
                    route="rag_answer_rerank_stream",
                    question=payload.query,
                    answer=result.get("answer") or "",
                    evidence=guardrail_evidence,
                    model=result.get("model"),
                    latency_ms=latency_ms,
                    guardrail_meta=guardrail_meta,
                )
            except Exception:
                pass
            await queue.put(("final", {"response": result}))
        except Exception as exc:
            logger.exception("rag_answer_rerank_stream failed", exc_info=exc)
            await queue.put(("error", {"message": "internal_error"}))
        finally:
            await queue.put(None)

    async def event_stream():
        # Emit a first chunk immediately to avoid proxy/client buffering.
        yield _format_sse("status", {"status": "start", "meta": {"query": payload.query, "top_k": payload.top_k}})
        task = asyncio.create_task(runner())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=keepalive_seconds)
                except asyncio.TimeoutError:
                    yield _format_sse_comment(f"keepalive {datetime.now(timezone.utc).isoformat()}")
                    if await request.is_disconnected():
                        task.cancel()
                        break
                    continue
                if item is None:
                    break
                event, data = item
                yield _format_sse(event, data)
                if await request.is_disconnected():
                    task.cancel()
                    break
        except asyncio.CancelledError:
            task.cancel()
            raise

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@ragLLMRou.post("/feedback", response_model=FeedbackCreateResponse)
async def submit_feedback(
    payload: FeedbackCreateRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    await log_feedback_event(payload, zjwt, db)
    return FeedbackCreateResponse()
