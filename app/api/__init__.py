from fastapi import APIRouter

from .root import rouRoot
from .mcp import rouMcp
from .agents import agentsRou
from .triage import rouTriage
from .sessions import rouAcc

rou = APIRouter()

rou.include_router(rouRoot,  tags=["Root"])

rou.include_router(rouAcc, tags=["Sessions"])

rou.include_router(agentsRou, tags=["Agents"])
rou.include_router(rouMcp, tags=["MCP"])
rou.include_router(rouTriage, tags=["Triage"])
