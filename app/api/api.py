
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Session token tracking
session_token_usage = {}  # session_id -> {"total_input": int, "total_output": int}


# --- End of Inlined Decision Tree Logic ---


# Initialize MCP manager after function definitions
mcp_manager.initialize_default_clients()
add_server_log("system", f"MCP Manager initialized with clients: {mcp_manager.get_active_clients()}", level="info", details={"active_clients": mcp_manager.get_active_clients()})

# Pre-load tools cache
refresh_tools_cache()




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

