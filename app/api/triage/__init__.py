from fastapi import APIRouter, HTTPException

from app.observability import server_logging, http_logging
import  app.globals as g 

rouTriage = APIRouter()


# Decision Tree Graph and Triage APIs
@rouTriage.get("/api/decision-tree")
async def get_decision_tree():
    """Get the decision tree structure for visualization"""
    try:
        
        # Convert decision tree to JSON-serializable format
        tree_data = {}
        for node_id, node in g.decision_tree.nodes.items():
            tree_data[node_id] = {
                "id": node.id,
                "topic": node.topic,
                "question": node.question,
                "ui_display": node.ui_display,
                "response_options": node.response_options,
                "children": node.children,
                "is_terminal": node.is_terminal,
                "outcome": node.outcome
            }
        
        return {
            "nodes": tree_data,
            "total_nodes": len(tree_data),
            "entry_point": "start"
        }
        
    except Exception as e:
        server_logging.add_server_log("triage", f"Error getting decision tree: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail="Failed to retrieve decision tree")

@rouTriage.get("/api/triage/session/{session_id}")
async def get_triage_session_state(session_id: str):
    """Get the current state of a triage session"""
    try:
        server_logging.add_server_log("triage", f"Session state requested: {session_id}", level="info")
        
        if not g.decision_tree:
            server_logging.add_server_log("triage", "Decision tree not initialized for session request", level="warning")
            return {"error": "Decision tree not initialized"}
        
        if session_id not in g.decision_tree.conversations:
            server_logging.add_server_log("triage", f"Session not found: {session_id}", level="info")
            return {
                "session_id": session_id,
                "exists": False,
                "message": "Session not found"
            }
        
        session_state = g.decision_tree.conversations[session_id]
        current_node = g.decision_tree.nodes.get(session_state.current_node_id)
        
        if not current_node:
            server_logging.add_server_log("triage", f"Invalid session state for {session_id}: node {session_state.current_node_id} not found", level="error")
            raise HTTPException(status_code=500, detail="Invalid session state")
        
        server_logging.add_server_log("triage", f"SESSION STATE API: {session_id} at node {current_node.id}", level="info", details={
            "session_id": session_id,
            "current_node": current_node.id,
            "current_topic": current_node.topic,
            "is_terminal": current_node.is_terminal,
            "children_count": len(current_node.children),
            "response_options_count": len(current_node.response_options),
            "created_at": session_state.created_at.isoformat(),
            "last_updated": session_state.last_updated.isoformat()
        })
        
        return {
            "session_id": session_id,
            "exists": True,
            "current_node_id": session_state.current_node_id,
            "current_node": {
                "id": current_node.id,
                "topic": current_node.topic,
                "question": current_node.question,
                "ui_display": current_node.ui_display,
                "response_options": current_node.response_options,
                "is_terminal": current_node.is_terminal,
                "outcome": current_node.outcome
            },
            "conversation_history": session_state.conversation_history,
            "user_responses": session_state.user_responses,
            "reasoning_trail": session_state.reasoning_trail,
            "chat_mode": session_state.chat_mode,
            "completed": session_state.completed,
            "created_at": session_state.created_at.isoformat(),
            "last_updated": session_state.last_updated.isoformat()
        }
        
    except Exception as e:
        server_logging.add_server_log("triage", f"Error getting triage session: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail="Failed to retrieve triage session")

@rouTriage.get("/api/triage/status")
async def get_triage_system_status():
    """Get the status of the AI Triage Agent system"""
    try:
        global decision_tree

        if not decision_tree:
            server_logging.add_server_log("triage", "Decision tree not initialized", level="warning")
            return {
                "status": "offline",
                "message": "Decision tree not initialized",
                "nodes_loaded": 0,
                "tree": None
            }

        # Convert decision tree to JSON-serializable format for visualization
        tree_data = {}
        for node_id, node in decision_tree.nodes.items():
            tree_data[node_id] = {
                "id": node.id,
                "topic": node.topic,
                "question": node.question,
                "children": node.children,
                "is_terminal": node.is_terminal,
                "outcome": node.outcome
            }

        return {
            "status": "online",
            "nodes_loaded": len(decision_tree.nodes) if decision_tree.nodes else 0,
            "tree": {"nodes": tree_data},
            "message": "AI Triage Agent system ready"
        }
        
    except Exception as e:
        server_logging.add_server_log("triage", f"Triage system error: {str(e)}", level="error")
        return {
            "status": "offline", 
            "message": "Triage system unavailable",
            "nodes_loaded": 0,
            "tree": None
        }
