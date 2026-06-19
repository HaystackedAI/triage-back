from typing import Dict, List
from datetime import datetime
from app.observability import server_logging
from app.data.decisiontree_type import DecisionTree
from app.mcp_conn.mcpmanager import mcp_manager
# initialized during startup
decision_tree: DecisionTree | None = None

# session cache
session_agents = {}

# tool cache
cached_tools = []
tools_last_updated = None

# token usage
session_token_usage = {}


# Store server logs
mcp_servers = {}  # Initialize early to avoid loading issues
server_logs: Dict[str, List[str]] = {}
    
def refresh_tools_cache():
    """Refresh the global tools cache"""
    global cached_tools, tools_last_updated

    try:
        server_logging.add_server_log("system", "Attempting to get tools from mcp_manager...", level="info")
        active_clients = mcp_manager.get_active_clients()
        server_logging.add_server_log("system", f"Active MCP clients: {active_clients}", level="info")

        cached_tools = mcp_manager.get_all_tools(active_only=True)
        tools_last_updated = datetime.now()
        tool_names = [getattr(tool, 'tool_name', str(type(tool).__name__)) for tool in cached_tools]
        server_logging.add_server_log("system", f"Tools cache refreshed: {len(cached_tools)} tools - {tool_names}", level="info", details={"tool_count": len(cached_tools), "tool_names": tool_names})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        server_logging.add_server_log("system", f"Error refreshing tools cache: {str(e)}", level="error", details={"error": str(e), "traceback": error_detail})
        cached_tools = []


def get_cached_tools():
    """Get cached tools, refresh if empty"""
    global cached_tools
    
    if not cached_tools:
        refresh_tools_cache()
    
    return cached_tools
