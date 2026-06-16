from fastapi import APIRouter

from .t4_employee import employeeRou
from .t4_entry import entryRou
from .t4_history import historyRou
from .t4_period import periodRou
from .t4_schedule import scheduleRou

rouT4 = APIRouter()

@app.get("/mcp/servers")
async def get_mcp_servers():
    """Get all MCP servers with their current status"""
    return mcp_servers

class ToggleRequest(BaseModel):
    enabled: bool

@app.post("/mcp/servers/{server_name}/toggle")
async def toggle_mcp_server(server_name: str, request: ToggleRequest):
    """Toggle MCP server enabled/disabled state"""
    global mcp_servers
    
    if server_name not in mcp_servers:
        raise HTTPException(status_code=404, detail="Server not found")
    
    enabled = request.enabled
    
    # Update server state
    mcp_servers[server_name]["enabled"] = enabled
    mcp_servers[server_name]["status"] = "ready" if enabled else "disabled"
    
    # Save to configuration file
    save_mcp_config(mcp_servers)
    
    # Update MCP client active state and refresh agent cache
    mcp_manager.set_client_active(server_name, enabled)
    refresh_agents()
    
    action = "enabled" if enabled else "disabled"
    add_server_log(server_name, f"Server {action}")
    
    return {"success": True, "server": server_name, "enabled": enabled}

@app.get("/mcp/logs")
async def get_mcp_logs():
    return server_logs

@app.delete("/mcp/logs")
async def clear_mcp_logs():
    global server_logs
    server_logs.clear()
    add_server_log("system", "Logs cleared")
    return {"message": "Logs cleared"}

@app.post("/mcp/initialize")
async def initialize_mcp():
    """Initialize all MCP servers"""
    try:
        initialize_mcp_servers()
        mcp_manager.initialize_default_clients()
        refresh_agents()  # This will refresh tools cache and clear agents
        return {"message": "MCP servers initialized", "status": "success"}
    except Exception as e:
        add_server_log("system", f"Initialization error: {str(e)}")
        return {"message": "Initialization failed", "status": "error"}

@app.get("/mcp/tools")
async def get_mcp_tools_endpoint():
    """Get all available MCP tools from cache"""
    try:
        tools = get_cached_tools()
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
            "last_updated": tools_last_updated.isoformat() if tools_last_updated else None
        }
    except Exception as e:
        logger.error(f"Error retrieving MCP tools: {str(e)}")
        return {"error": "Failed to retrieve MCP tools", "tools": [], "count": 0}
