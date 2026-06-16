"""
AI Triage Agent - Backend
Real Strands Agent integration with MCP servers
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict, field
import re

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters, stdio_client
from mcpmanager import mcp_manager

from observability.server_logging import add_server_log

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store server logs
mcp_servers = {}  # Initialize early to avoid loading issues
mcp_clients = {}  # Store MCP client instances


# Global agent cache - session-based
session_agents = {}

# Global tools cache
cached_tools = []
tools_last_updated = None

# Session token tracking
session_token_usage = {}  # session_id -> {"total_input": int, "total_output": int}


# --- End of Inlined Decision Tree Logic ---


# Initialize MCP manager after function definitions
mcp_manager.initialize_default_clients()
add_server_log("system", f"MCP Manager initialized with clients: {mcp_manager.get_active_clients()}", level="info", details={"active_clients": mcp_manager.get_active_clients()})

# Pre-load tools cache
refresh_tools_cache()


def get_session_messages_for_ui(session_id: str, model_id: str) -> List[Dict]:
    """Get session messages formatted for UI from the actual agent"""
    agent_key = f"{session_id}:{model_id}"
    
    if agent_key not in session_agents:
        return []
    
    agent = session_agents[agent_key]
    
    # Get messages from agent.messages
    if not hasattr(agent, 'messages') or not agent.messages:
        return []
    
    ui_messages = []
    
    for msg in agent.messages:
        # Skip system messages
        if msg.get('role') == 'system':
            continue
            
        # Convert Strands message format to UI format
        if msg.get('role') in ['user', 'assistant']:
            message_content = ""
            
            # Extract content from Strands message format
            content = msg.get('content', [])
            if isinstance(content, str):
                message_content = content
            elif isinstance(content, list):
                text_parts = []
                for content_item in content:
                    if isinstance(content_item, dict):
                        if 'text' in content_item:
                            text_parts.append(content_item['text'])
                        elif 'toolUse' in content_item:
                            tool_use = content_item['toolUse']
                            text_parts.append(f"🔧 Used tool: {tool_use.get('name', 'unknown')}")
                        elif 'toolResult' in content_item:
                            tool_result = content_item['toolResult']
                            if 'content' in tool_result and tool_result['content']:
                                result_text = tool_result['content'][0].get('text', '') if tool_result['content'] else ''
                                text_parts.append(f"✅ Result: {result_text[:100]}...")
                    else:
                        text_parts.append(str(content_item))
                message_content = "\n".join(text_parts)
            
            ui_messages.append({
                "id": len(ui_messages) + 1,
                "role": msg['role'],
                "content": message_content,
                "timestamp": datetime.now().isoformat(),  # We don't have original timestamp
                "model": model_id if msg['role'] == 'assistant' else None
            })
    
    return ui_messages

def refresh_agents():
    """Refresh tools cache and clear agent cache"""
    global session_agents
    
    # Refresh tools cache first
    refresh_tools_cache()
    
    # Clear agent cache so they get recreated with new tools
    session_agents.clear()
    add_server_log("system", "Tools and agent cache refreshed - agents will recreate with new tools", level="info", details={"cleared_sessions": len(session_agents)})


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: ~4 chars per token)"""
    if not text:
        return 0
    # Simple and conservative estimation: 4 characters per token
    return max(1, len(text) // 4)


def get_all_mcp_tools():
    """Get all tools from MCP servers"""
    all_tools = []
    
    for server_name, mcp_client in mcp_clients.items():
        try:
            # Note: We don't use 'with' here as tools are used later in the agent
            # The agent will handle the context when it uses the tools
            tools = mcp_client.list_tools_sync()
            if tools:
                all_tools.extend(tools)
                add_server_log(server_name, f"Loaded {len(tools)} tools")
        except Exception as e:
            add_server_log(server_name, f"Tool loading error: {str(e)}")
    
    return all_tools

# Available models with new Claude versions

# Initialize Strands Agents for different models
agents_cache = {}

def create_mcp_agent_tools():
    """Create MCP tools that can be used by the agent"""
    from strands import tool
    
    mcp_tools = []
    
    for server_name, mcp_client in mcp_clients.items():
        if not mcp_servers[server_name].get("enabled", True):
            continue
            
        # Create a tool function for each MCP server
        @tool
        def mcp_server_tool(query: str, server_name=server_name, client=mcp_client) -> str:
            f"""
            Interact with {server_name} MCP server

            Args:
                query: The user's query or command

            Returns:
                Response from the MCP server
            """
            try:
                with client:
                    tools = client.list_tools_sync()
                    if tools:
                        # For now, we'll use the first available tool
                        # In a real implementation, you'd parse the query and select the appropriate tool
                        return f"MCP server {server_name} has {len(tools)} available tools"
                    else:
                        return f"No tools available on {server_name} server"
            except Exception as e:
                add_server_log("mcp", f"Error accessing {server_name} server: {str(e)}", level="error")
                return "Error accessing MCP server"
        
        # Set the tool name dynamically
        mcp_server_tool.__name__ = f"{server_name}_tool"
        mcp_tools.append(mcp_server_tool)
    
    return mcp_tools

def get_strands_agent(model_id: str):
    """Get or create a Strands agent for the specified model"""
    try:
        add_server_log("system", f"Creating agent for {model_id}")
        
        # Create Bedrock model instance
        bedrock_model = BedrockModel(
            model_id=model_id,
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            temperature=0.7,
        )
        
        # Get MCP tools
        mcp_tools = create_mcp_agent_tools()
        
        # Create agent with MCP tools integration
        system_prompt = f"""You are a helpful AI assistant for AI Triage Agent. 
You have access to various tools and services through MCP servers.

Available MCP servers: {len(mcp_clients)} servers

Always provide clear, accurate, and helpful responses in markdown format when appropriate.
Use the available tools when relevant to answer user questions. Analyze the user's request
and determine which tools would be most helpful to provide a complete response."""
        
        agent = Agent(
            model=bedrock_model,
            system_prompt=system_prompt,
            tools=mcp_tools if mcp_tools else None
        )
        
        add_server_log("system", f"Agent ready with {len(mcp_tools)} MCP tools: {model_id}")
        return agent
        
    except Exception as e:
        logger.error(f"Error creating Strands agent for {model_id}: {str(e)}")
        add_server_log("system", f"Agent error: {str(e)[:50]}...")
        raise



async def stream_plain_text_response_generator(text: str, model_id: str, tokens: Dict[str, int]):
    """An async generator to stream a plain text response chunk by chunk."""
    # Stream back the response word by word
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk_data = {
            "type": "textDelta",
            "text": f" {word}" if i > 0 else word,
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
        await asyncio.sleep(0.02)

    # Send final message with token usage
    final_chunk = {
        "type": "messageDelta",
        "delta": {"role": "assistant"},
        "usage": {"output_tokens": tokens.get("output", 0)}
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"

    # Send message stop
    stop_chunk = {
        "type": "messageStop",
    }
    yield f"data: {json.dumps(stop_chunk)}\n\n"

