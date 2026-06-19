from datetime import datetime
from typing import List, Dict
import inspect

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
import app.globals as g
from app.mcp_conn.mcpmanager import mcp_manager
from app.observability import server_logging, http_logging

def refresh_tools_cache():
    """Refresh the global tools cache"""
    
    try:
        g.cached_tools = mcp_manager.get_all_tools(active_only=True)
        g.tools_last_updated = datetime.now()
        server_logging.add_server_log("system", f"Tools cache refreshed: {len(g.cached_tools)} tools loaded", level="info", details={"tool_count": len(g.cached_tools)})
    except Exception as e:
        server_logging.add_server_log("system", f"Error refreshing tools cache: {str(e)}", level="error", details={"error": str(e)})
        g.cached_tools = []

def get_cached_tools():
    if not g.cached_tools: refresh_tools_cache()
    return g.cached_tools


def get_or_create_session_agent(session_id: str, model_id: str) -> Agent:
    """Get or create a cached agent for the given session and model"""
    func_name = inspect.currentframe().f_code.co_name
    agent_key = f"{session_id}:{model_id}"
    server_logging.add_server_log(func_name, f"Model: {model_id}", level="warning")

    if agent_key not in g.session_agents:
        model = BedrockModel(model_id=model_id, temperature=0.7)
        tools = get_cached_tools()
        tool_names = [getattr(tool, 'tool_name', str(type(tool).__name__)) for tool in tools]
        server_logging.add_server_log(func_name, f"Tools loaded: {len(tools)} tools - {tool_names}", level="info")
        
        # General purpose prompt. Specific instructions will be provided in each call.
        system_prompt = """You are a helpful and knowledgeable person.
                    You must follow the specific instructions given in each prompt precisely.
                    Always provide your response in a clear, conversational, and professional manner.
                    The user-facing response must NOT include any system commands or XML tags unless specifically requested.

                    TOOL USAGE:
                    You have access to calculator, task manager, calendar, weather, and email tools.
                    When users ask questions that can be answered with these tools, USE THEM:
                    - Math questions (dividend yield, compound growth, tax savings) → use calculator tools
                    - Action items and reminders → use task_manager tools
                    - Scheduling (dividend payment dates, account opening) → use calendar tools
                    - Weather inquiries → use weather tools
                    - Email queries → use email_history tools

                    EXPENSE TRACKING TOOLS:
                    For expense tracking tools (get_balance, add_expense, add_income, set_budget), always use:
                    - user_alias: "kevin@datamond.ai"
                    This is the authenticated user. Never ask the user for their alias, always use this value.

                    FORMATTING GUIDELINES:
                    - Use **bold text** for important financial concepts, warnings, or key recommendations
                    - Use clear, conversational language that investors can easily understand
                    - Highlight important strategy points and action items with appropriate emphasis
                    - Make financial calculations and recommendations stand out visually
                    - Always include disclaimers that this is educational content, not financial advice
                """
        
        agent = Agent(model=model, system_prompt=system_prompt, tools=tools)
        g.session_agents[agent_key] = agent
        server_logging.add_server_log("system", f"[AGENT] Session agent cached for {agent_key}")
    
    return g.session_agents[agent_key]


def refresh_agents():
    """Refresh tools cache and clear agent cache"""
    
    # Refresh tools cache first
    refresh_tools_cache()
    
    # Clear agent cache so they get recreated with new tools
    g.session_agents.clear()
    server_logging.add_server_log("system", "Tools and agent cache refreshed - agents will recreate with new tools", level="info", details={"cleared_sessions": len(g.session_agents)})
