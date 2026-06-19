"""Check what tools the agent actually has"""
import sys
sys.path.insert(0, 'app')

import app.globals as g
from app.mcp_conn.mcpmanager import mcp_manager
from app.agents.triage_agent import get_or_create_session_agent

# Initialize like the app does
mcp_manager.initialize_default_clients()
g.refresh_tools_cache()

print(f"\nCached tools count: {len(g.cached_tools)}")
print("\nCached tool names:")
for tool in g.cached_tools:
    tool_name = getattr(tool, 'tool_name', 'unknown')
    server = mcp_manager.get_server_for_tool(tool_name)
    print(f"  - {tool_name} (from {server})")

# Create an agent
print("\n" + "="*60)
print("Creating agent...")
agent = get_or_create_session_agent("test_session", "us.amazon.nova-pro-v1:0")

print(f"\nAgent tools count: {len(agent.tools) if hasattr(agent, 'tools') else 0}")
print("\nAgent tool names:")
if hasattr(agent, 'tools'):
    for tool in agent.tools:
        tool_name = getattr(tool, 'tool_name', getattr(tool, 'name', 'unknown'))
        print(f"  - {tool_name}")
