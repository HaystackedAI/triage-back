"""MCP Server Configuration

This module defines all MCP server configurations.
Imported directly instead of reading from JSON file for better type safety and performance.
"""

# Common AgentCore defaults
AGENTCORE_DEFAULTS = {
    "transport": "agentcore",
    "region": "us-east-1",
    "cognito_user_pool_id": "us-east-1_IsYqleAY1",
    "cognito_client_id": "6i47v4nd15s0rfr07k4c4n9k1u",
    "cognito_username": "kevin@datamond.ai",
    "cognito_password": "NewStrongPassw0rd!2026"
}

MCP_SERVERS = {
    "expense_tracker": {
        **AGENTCORE_DEFAULTS,
        "runtime_name": "mcpe2e_e2e-bm14m2AQY9",
        "enabled": True
    },
    "calculator": {
        **AGENTCORE_DEFAULTS,
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp1_Cal-3WVTZZ55XO",
        "enabled": True
    },
    "weather": {
        **AGENTCORE_DEFAULTS,
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp2_Weather-a7ZoanFkS0",
        "enabled": True
    },
    "task_manager": {
        **AGENTCORE_DEFAULTS,
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp4_Task-nmaGy55hAz",
        "enabled": False
    }
}
