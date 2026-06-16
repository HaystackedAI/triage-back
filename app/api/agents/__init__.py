from fastapi import APIRouter
from .inv2_invoices import inv2Rou 
from .inv1_home import homeRou

from .settings import settingsRou

invRou = APIRouter()

@app.get("/agents/status")
async def get_agents_status():
    """Get cached session agents status"""
    agents_info = {}
    for agent_key, agent in session_agents.items():
        session_id, model_id = agent_key.split(":", 1)
        agents_info[agent_key] = {
            "session_id": session_id,
            "model_id": model_id,
            "created": True,
            "tools_count": len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0
        }
    
    return {
        "session_agents": agents_info,
        "count": len(session_agents)
    }

@app.post("/agents/refresh")
async def refresh_agents_endpoint():
    """Refresh all cached agents"""
    refresh_agents()
    return {"message": "Agent cache refreshed", "status": "success"}
