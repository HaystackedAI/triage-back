from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import HTTPException
from app.mcp_conn import mcp_main
from app.mcp_conn.mcpmanager import mcp_manager
from app.agents.triage_agent import refresh_agents
from app.observability import server_logging, http_logging
import app.globals as g

rouMcp = APIRouter()

@rouMcp.get("/mcp/servers")
async def get_mcp_servers():
    """Get all MCP servers with their current status"""
    return g.mcp_servers
    
class ToggleRequest(BaseModel):
    enabled: bool

@rouMcp.post("/mcp/servers/{server_name}/toggle")
async def toggle_mcp_server(server_name: str, request: ToggleRequest):
    """Toggle MCP server enabled/disabled state"""
    
    if server_name not in g.mcp_servers: raise HTTPException(status_code=404, detail="Server not found")
    
    enabled = request.enabled
    
    # Update server state
    g.mcp_servers[server_name]["enabled"] = enabled
    g.mcp_servers[server_name]["status"] = "ready" if enabled else "disabled"
    
    # Save to configuration file
    mcp_main.save_mcp_config(g.mcp_servers)
    
    # Update MCP client active state and refresh agent cache
    mcp_manager.set_client_active(server_name, enabled)
    refresh_agents()
    
    action = "enabled" if enabled else "disabled"
    server_logging.add_server_log(server_name, f"Server {action}")
    
    return {"success": True, "server": server_name, "enabled": enabled}

@rouMcp.get("/mcp/logs")
async def get_mcp_logs():
    # return "---"
    return g.server_logs
    

@rouMcp.delete("/mcp/logs")
async def clear_mcp_logs():
    g.server_logs.clear()
    server_logging.add_server_log("system", "Logs cleared")
    return {"message": "Logs cleared"}

@rouMcp.post("/mcp/initialize")
async def initialize_mcp():
    """Initialize all MCP servers"""
    try:
        mcp_manager.initialize_default_clients()
        refresh_agents()  # This will refresh tools cache and clear agents
        return {"message": "MCP servers initialized", "status": "success"}
    except Exception as e:
        server_logging.add_server_log("system", f"Initialization error: {str(e)}")
        return {"message": "Initialization failed", "status": "error"}

@rouMcp.get("/mcp/tools")
async def get_mcp_tools_endpoint():
    """Get all available MCP tools from cache"""
    try:
        tools = g.get_cached_tools()
        tool_info = []
        
        for tool in tools:
            # Extract tool information safely
            tool_data = {
                "name": getattr(tool, 'name', 'unknown'),
                "description": getattr(tool, 'description', ''),
                "type": tool.__class__.__name__
            }
            tool_info.append(tool_data)
        
        return {
            "tools": tool_info,
            "count": len(tools),
            "last_updated": g.tools_last_updated.isoformat() if g.tools_last_updated else None
        }
    except Exception as e:
        server_logging.add_server_log("system", f"Error retrieving MCP tools: {str(e)}", level="error")
        return {"error": "Failed to retrieve MCP tools", "tools": [], "count": 0}
