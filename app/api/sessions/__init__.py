from fastapi import APIRouter
from app.observability import server_logging, http_logging
from app.sessions import get_session_messages_for_ui

rouAcc = APIRouter()

@rouAcc.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session's agent and triage session"""
    global session_agents, decision_tree
    
    # Remove all agents for this session
    keys_to_remove = [key for key in session_agents.keys() if key.startswith(f"{session_id}:")]
    for key in keys_to_remove:
        del session_agents[key]
    
    # Remove triage session if exists
    if decision_tree and session_id in decision_tree.conversations:
        del decision_tree.conversations[session_id]
        server_logging.add_server_log("triage", f"Cleared triage session: {session_id}")
    
    server_logging.add_server_log("system", f"Cleared session: {session_id}")
    return {"message": f"Session {session_id} cleared", "status": "success"}

@rouAcc.get("/sessions")
async def get_sessions():
    """Get all active sessions"""
    sessions = {}
    for agent_key in session_agents.keys():
        session_id, model_id = agent_key.split(":", 1)
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append(model_id)
    
    return {"sessions": sessions, "count": len(sessions)}

@rouAcc.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"):
    """Get message history for a specific session"""
    
    # Check if the session exists in our in-memory store
    try:
        # Get messages from the actual agent
        messages = get_session_messages_for_ui(session_id, model_id)
        
        agent_key = f"{session_id}:{model_id}"
        exists = agent_key in session_agents
        
        server_logging.add_server_log("system", f"Session history request: {session_id} - Found {len(messages)} messages, exists: {exists}")
        
        return {
            "messages": messages,
            "session_id": session_id,
            "model_id": model_id,
            "exists": exists,
            "count": len(messages)
        }
        
    except Exception as e:
        server_logging.add_server_log("system", f"Error getting session history: {str(e)}")
        return {"messages": [], "session_id": session_id, "exists": False, "error": "Failed to retrieve session history"}

