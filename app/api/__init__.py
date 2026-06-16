from fastapi import APIRouter

from .root import rouRoot
from .mcp import rouMcp
from .agents import agentsRou
from .triage import rouBI
from .sessions import rouAcc

rou = APIRouter()

rou.include_router(rouRoot, prefix="/too", tags=["too"])

rou.include_router(rouAcc, prefix="/acc", tags=["acc"])
rou.include_router(rouAI,  prefix="/ai", tags=["ai"])

rou.include_router(agentsRou, prefix="/inv")
rou.include_router(rouMcp, prefix="/t4", tags=["t4"])
rou.include_router(rouBI, prefix="/bi", tags=["bi"])
