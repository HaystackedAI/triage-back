from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.sch_ai import JWType

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.rag.eva.answer_relevance import run_answer_relevance
from app.rag.eva.answer_similarity import run_answer_similarity
from app.rag.eva.faithfulness import run_faithfulness
from app.rag.eva.precision_at_k import run_precision_at_k
from app.rag.eva.recall_at_k import run_recall_at_k
from app.schemas.sch_ai_gold_dataset import (
    GoldDatasetCreateRequest,
    GoldDatasetOut,
    GoldDatasetUpdateRequest,
)
from app.schemas.sch_ai_rag_answer_relevance import (
    RagEvalAnswerRelevanceRequest,
    RagEvalAnswerRelevanceResponse,
)
from app.schemas.sch_ai_rag_answer_similarity import (
    RagEvalAnswerSimilarityRequest,
    RagEvalAnswerSimilarityResponse,
)
from app.schemas.sch_ai_rag_eval import RagEvalRequest, RagEvalResponse
from app.schemas.sch_ai_rag_faithfulness import (
    RagEvalFaithfulnessRequest,
    RagEvalFaithfulnessResponse,
)
from app.schemas.sch_ai_rag_overall import RagEvalOverallRequest, RagEvalOverallResponse
from app.schemas.sch_ai_rag_precision import RagEvalPrecisionRequest, RagEvalPrecisionResponse
from app.schemas.sch_ai_rag_recall import RagEvalRecallRequest, RagEvalRecallResponse
from app.schemas.sch_ai_rag_run_rfr import RagEvalRunRFRRequest, RagEvalRunRFRResponse
from app.service.ser_ai_gold_dataset import create_gold_dataset, list_gold_dataset, update_gold_dataset
from app.service.ser_ai_rag_eval import run_rag_eval

ragEvalRou = APIRouter()


def _to_gold_out(row) -> GoldDatasetOut:
    return GoldDatasetOut(
        id=str(row.id),
        question=row.question,
        expected_answer=row.expected_answer,
        relevant_source_ids=[str(x) for x in (row.relevant_source_ids or [])],
        category=row.category,
        difficulty=row.difficulty,
        is_active=bool(row.is_active),
    )


@ragEvalRou.get("/dataset/list", response_model=list[GoldDatasetOut])
async def dataset_list(
    limit: int = Query(200, ge=1, le=1000),
    _zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    rows = await list_gold_dataset(limit, db)
    return [_to_gold_out(row) for row in rows]


@ragEvalRou.post("/dataset/create", response_model=GoldDatasetOut)
async def dataset_create(
    payload: GoldDatasetCreateRequest,
    _zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    row = await create_gold_dataset(payload, db)
    return _to_gold_out(row)


# @ragEvalRou.post("/dataset/update", response_model=GoldDatasetOut)
# async def dataset_update(
#     payload: GoldDatasetUpdateRequest,
#     _zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     row = await update_gold_dataset(payload, db)
#     return _to_gold_out(row)


# @ragEvalRou.post("/run", response_model=RagEvalResponse)
# async def run_rag_eval_endpoint(
#     payload: RagEvalRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     return await run_rag_eval(payload, ctx)


# @ragEvalRou.post("/run-judge", response_model=RagEvalResponse)
# async def run_rag_eval_judge_endpoint(
#     payload: RagEvalRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     judge_payload = payload.model_copy(update={"judge": True})
#     return await run_rag_eval(judge_payload, ctx)


# @ragEvalRou.post("/run-heuristic", response_model=RagEvalResponse)
# async def run_rag_eval_heuristic_endpoint(
#     payload: RagEvalRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     heuristic_payload = payload.model_copy(update={"judge": False})
#     return await run_rag_eval(heuristic_payload, ctx)


# @ragEvalRou.post("/run-summary", response_model=RagEvalResponse)
# async def run_rag_eval_summary_endpoint(
#     payload: RagEvalRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     summary_payload = payload.model_copy(update={"include_rows": False, "include_failures": False})
#     return await run_rag_eval(summary_payload, ctx)


# @ragEvalRou.post("/recall_at_k", response_model=RagEvalRecallResponse)
# async def run_rag_eval_recall_at_k_endpoint(
#     payload: RagEvalRecallRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     return await run_recall_at_k(payload, ctx)


# @ragEvalRou.post("/precision_at_k", response_model=RagEvalPrecisionResponse)
# async def run_rag_eval_precision_at_k_endpoint(
#     payload: RagEvalPrecisionRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     return await run_precision_at_k(payload, ctx)


# @ragEvalRou.post("/faithfulness", response_model=RagEvalFaithfulnessResponse)
# async def run_rag_eval_faithfulness_endpoint(
#     payload: RagEvalFaithfulnessRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     return await run_faithfulness(payload, ctx)


# @ragEvalRou.post("/answer_similarity", response_model=RagEvalAnswerSimilarityResponse)
# async def run_rag_eval_answer_similarity_endpoint(
#     payload: RagEvalAnswerSimilarityRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     return await run_answer_similarity(payload, ctx)


# @ragEvalRou.post("/answer_relevance", response_model=RagEvalAnswerRelevanceResponse)
# async def run_rag_eval_answer_relevance_endpoint(
#     payload: RagEvalAnswerRelevanceRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     return await run_answer_relevance(payload, ctx)


# @ragEvalRou.post("/run_recall_faithfulness_relevance", response_model=RagEvalRunRFRResponse)
# async def run_rag_eval_recall_faithfulness_relevance_endpoint(
#     payload: RagEvalRunRFRRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     recall = await run_recall_at_k(
#         RagEvalRecallRequest(
#             top_k=payload.top_k,
#             limit=payload.limit,
#             category=payload.category,
#             description=f"{payload.description} (recall@k)",
#             include_rows=payload.include_rows,
#         ),
#         ctx,
#     )
#     faithfulness = await run_faithfulness(
#         RagEvalFaithfulnessRequest(
#             top_k=payload.top_k,
#             limit=payload.limit,
#             category=payload.category,
#             description=f"{payload.description} (faithfulness)",
#             judge=payload.judge,
#             include_rows=payload.include_rows,
#         ),
#         ctx,
#     )
#     relevance = await run_answer_relevance(
#         RagEvalAnswerRelevanceRequest(
#             top_k=payload.top_k,
#             limit=payload.limit,
#             category=payload.category,
#             description=f"{payload.description} (relevance)",
#             include_rows=payload.include_rows,
#         ),
#         ctx,
#     )
#     return RagEvalRunRFRResponse(recall=recall, faithfulness=faithfulness, relevance=relevance)


# @ragEvalRou.post("/run_overall_score", response_model=RagEvalOverallResponse)
# async def run_rag_eval_overall_score_endpoint(
#     payload: RagEvalOverallRequest,
#     zjwt: JWType = Depends(get_zjwt),
#     db: AsyncSession = Depends(get_pgconn),
# ):
#     ctx = ai_context_from_zjwt(zjwt, db)
#     recall = await run_recall_at_k(
#         RagEvalRecallRequest(
#             top_k=payload.top_k,
#             limit=payload.limit,
#             category=payload.category,
#             description=f"{payload.description} (recall@k)",
#             include_rows=False,
#         ),
#         ctx,
#     )
#     faithfulness = await run_faithfulness(
#         RagEvalFaithfulnessRequest(
#             top_k=payload.top_k,
#             limit=payload.limit,
#             category=payload.category,
#             description=f"{payload.description} (faithfulness)",
#             judge=payload.judge,
#             include_rows=False,
#         ),
#         ctx,
#     )
#     relevance = await run_answer_relevance(
#         RagEvalAnswerRelevanceRequest(
#             top_k=payload.top_k,
#             limit=payload.limit,
#             category=payload.category,
#             description=f"{payload.description} (relevance)",
#             include_rows=False,
#         ),
#         ctx,
#     )

#     recall_avg = recall.avg_recall_at_k
#     faith_avg = faithfulness.avg_faithfulness
#     relevance_avg = relevance.avg_answer_relevance

#     weighted_sum = 0.0
#     weight_total = 0.0
#     for value, weight in [
#         (recall_avg, payload.recall_weight),
#         (faith_avg, payload.faithfulness_weight),
#         (relevance_avg, payload.relevance_weight),
#     ]:
#         if value is None or weight <= 0:
#             continue
#         weighted_sum += value * weight
#         weight_total += weight

#     overall_score = None if weight_total == 0 else weighted_sum / weight_total
#     return RagEvalOverallResponse(
#         overall_score=overall_score,
#         recall_avg=recall_avg,
#         faithfulness_avg=faith_avg,
#         relevance_avg=relevance_avg,
#         weights={
#             "recall": payload.recall_weight,
#             "faithfulness": payload.faithfulness_weight,
#             "relevance": payload.relevance_weight,
#         },
#         run_ids={
#             "recall": recall.run_id,
#             "faithfulness": faithfulness.run_id,
#             "relevance": relevance.run_id,
#         },
#     )
