"""MCP Server Configuration

This module defines all MCP server configurations.
Imported directly instead of reading from JSON file for better type safety and performance.
"""

MCP_SERVERS = {
    "expense_tracker": {
        "transport": "agentcore",
        "runtime_name": "mcpe2e_e2e-bm14m2AQY9",
        "region": "us-east-1",
        "cognito_user_pool_id": "us-east-1_IsYqleAY1",
        "cognito_client_id": "6i47v4nd15s0rfr07k4c4n9k1u",
        "cognito_username": "kevin@datamond.ai",
        "cognito_password": "NewStrongPassw0rd!2026",
        "description": "Expense tracking tools (add_expense, add_income, set_budget, get_balance)",
        "enabled": True
    },
    "calculator": {
        "transport": "agentcore",
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp1_Cal-3WVTZZ55XO",
        "region": "us-east-1",
        "enabled": False
    },
    "weather": {
        "transport": "agentcore",
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp2_Weather-a7ZoanFkS0",
        "region": "us-east-1",
        "enabled": False
    },
    "task_manager": {
        "transport": "agentcore",
        "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:822206589627:runtime/mcp4_Task-nmaGy55hAz",
        "region": "us-east-1",
        "enabled": False
    }
}
