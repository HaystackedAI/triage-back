"""MCP Server Configuration

This module defines all MCP server configurations.
Imported directly instead of reading from JSON file for better type safety and performance.
"""

MCP_SERVERS = {
    "calculator": {
        "transport": "agentcore",
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp1_Cal-3WVTZZ55XO",
        "region": "us-east-1",
        "enabled": True
    },
    "weather": {
        "transport": "agentcore",
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp2_Weather-a7ZoanFkS0",
        "region": "us-east-1",
        "enabled": True
    },
    "task_manager": {
        "transport": "agentcore",
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp4_Task-nmaGy55hAz",
        "region": "us-east-1",
        "enabled": True
    },
    "calendar": {
        "command": "python",
        "args": [
            "app/mcp_local/calendar/calendar_server.py"
        ],
        "enabled": True,
        "transport": "stdio",
        "description": "Calendar server with date/time and event management tools"
    },
    "static": {
        "command": "python",
        "args": [
            "app/mcp_local/static/static.py"
        ],
        "enabled": True,
        "transport": "stdio",
        "description": "Static response test server with read/write tools"
    }
}
