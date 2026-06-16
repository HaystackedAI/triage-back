from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.schemas.sch_ai import JWType

langRou = APIRouter()


@langRou.post("/token")
async def get_token_count(request: dict):
    try:
        from app.langgraph.agent1.workflow.agent_1_workflow import compiled_workflow
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LangGraph not available: {exc}") from exc

    prompt = str(request.get("prompt") or "")
    initial_state = {
        "prompt": prompt,
        "llm_output": "",
        "token_count": 0,
    }
    result = compiled_workflow.invoke(initial_state)
    return {
        "prompt": result["prompt"],
        "llm_output": result["llm_output"],
        "token_count": result["token_count"],
    }
