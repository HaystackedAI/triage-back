from fastapi import APIRouter

from .root import rouToo
from .mcp import rouT4
from .agents import invRou
from .ai import rouAI
from .triage import rouBI
from .sessions import rouAcc

rou = APIRouter()

rou.include_router(rouToo, prefix="/too", tags=["too"])

rou.include_router(rouAcc, prefix="/acc", tags=["acc"])
rou.include_router(rouAI,  prefix="/ai", tags=["ai"])

rou.include_router(invRou, prefix="/inv")
rou.include_router(rouT4, prefix="/t4", tags=["t4"])
rou.include_router(rouBI, prefix="/bi", tags=["bi"])
