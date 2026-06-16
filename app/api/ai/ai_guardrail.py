from __future__ import annotations
from app.schemas.sch_ai import JWType

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_ai_guardrail import (
    GuardrailCostResponse,
    GuardrailLatencyResponse,
    GuardrailQueryRequest,
    GuardrailRateResponse,
)
# from app.service.ser_ai_context import ai_context_from_zjwt
from app.service.ser_ai_guardrail import compute_rate, fetch_values

guardrailRou = APIRouter()



def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if percentile <= 0:
        return min(values)
    if percentile >= 100:
        return max(values)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    rank = int((percentile / 100) * n)
    idx = max(0, min(n - 1, rank - 1))
    return sorted_vals[idx]


def _latency_stats(values: list[float]) -> GuardrailLatencyResponse:
    if not values:
        return GuardrailLatencyResponse(total=0)
    total = len(values)
    avg_ms = sum(values) / total
    return GuardrailLatencyResponse(
        total=total,
        avg_ms=avg_ms,
        p50_ms=_percentile(values, 50),
        p90_ms=_percentile(values, 90),
        p95_ms=_percentile(values, 95),
        p99_ms=_percentile(values, 99),
        min_ms=min(values),
        max_ms=max(values),
    )


def _cost_stats(values: list[float]) -> GuardrailCostResponse:
    if not values:
        return GuardrailCostResponse(total=0)
    total = len(values)
    total_usd = sum(values)
    avg_usd = total_usd / total
    return GuardrailCostResponse(
        total=total,
        total_usd=total_usd,
        avg_usd=avg_usd,
        p50_usd=_percentile(values, 50),
        p90_usd=_percentile(values, 90),
        p95_usd=_percentile(values, 95),
        p99_usd=_percentile(values, 99),
        min_usd=min(values),
        max_usd=max(values),
    )


@guardrailRou.post("/hallucination_rate", response_model=GuardrailRateResponse)
async def hallucination_rate(
    payload: GuardrailQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    ctx = ai_context_from_zjwt(zjwt, db)
    total, flagged, rate = await compute_rate(db, "is_hallucination", payload, ctx)
    return GuardrailRateResponse(total=total, flagged=flagged, rate=rate)


@guardrailRou.post("/refusal_rate", response_model=GuardrailRateResponse)
async def refusal_rate(
    payload: GuardrailQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    ctx = ai_context_from_zjwt(zjwt, db)
    total, flagged, rate = await compute_rate(db, "is_refusal", payload, ctx)
    return GuardrailRateResponse(total=total, flagged=flagged, rate=rate)


@guardrailRou.post("/fallback_rate", response_model=GuardrailRateResponse)
async def fallback_rate(
    payload: GuardrailQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    ctx = ai_context_from_zjwt(zjwt, db)
    total, flagged, rate = await compute_rate(db, "is_fallback", payload, ctx)
    return GuardrailRateResponse(total=total, flagged=flagged, rate=rate)


@guardrailRou.post("/latency", response_model=GuardrailLatencyResponse)
async def latency(
    payload: GuardrailQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    ctx = ai_context_from_zjwt(zjwt, db)
    values = await fetch_values(db, "latency_ms", payload, ctx)
    return _latency_stats(values)


@guardrailRou.post("/cost", response_model=GuardrailCostResponse)
async def cost(
    payload: GuardrailQueryRequest,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    ctx = ai_context_from_zjwt(zjwt, db)
    values = await fetch_values(db, "cost_usd", payload, ctx)
    return _cost_stats(values)
