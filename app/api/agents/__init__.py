from fastapi import APIRouter
from app.agents.triage_agent import refresh_agents
from app.agents import triage_agent
agentsRou = APIRouter()

@agentsRou.get("/agents/status")
async def get_agents_status():
    """Get cached session agents status"""
    agents_info = {}
    for agent_key, agent in triage_agent.items():
        session_id, model_id = agent_key.split(":", 1)
        agents_info[agent_key] = {
            "session_id": session_id,
            "model_id": model_id,
            "created": True,
            "tools_count": len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0
        }
    
    return {
        "session_agents": agents_info,
        "count": len(triage_agent)
    }

@agentsRou.post("/agents/refresh")
async def refresh_agents_endpoint():
    """Refresh all cached agents"""
    refresh_agents()
    return {"message": "Agent cache refreshed", "status": "success"}
