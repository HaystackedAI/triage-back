from fastapi import APIRouter

from .ai_brain import brainRou
from .ai_guardrail import guardrailRou
from .ai_langgraph import langRou
from .rag3_eval import ragEvalRou

from .rag1_unit import ragUnitRou
from .rag2_llm import ragLLMRou

rouAI = APIRouter()

rouAI.include_router(ragUnitRou, prefix="/rag1unit", tags=["rag-basic"])
rouAI.include_router(ragLLMRou, prefix="/rag2llm", tags=["rag-llm"])
rouAI.include_router(ragEvalRou, prefix="/rag3eval", tags=["rag-eval"])

rouAI.include_router(brainRou, prefix="/mcpbrain", tags=["ai-brain"])
rouAI.include_router(guardrailRou, prefix="/guardrail", tags=["ai-guardrail"])
rouAI.include_router(langRou, prefix="/langgraph", tags=["ai-langgraph"])
