import json
from typing import List, Dict, Any
import re
from datetime import datetime
from app.observability import server_logging, http_logging
from app.mcp_conn.mcpmanager import mcp_manager
import app.globals as g
from app.schema.root_schema import ImageData
from app.agents.triage_agent import get_or_create_session_agent

async def stream_ai_response_with_images(message: str, model_id: str, session_id: str = "default", images: List[ImageData] = None, history: List[Dict[str, Any]] = None):
    """Complete streaming with decision tree, XML processing, and node updates"""

    try:
        # server_logging.add_server_log("system", f"Processing [{session_id}]: {message[:30]}...")

        # Ensure session exists
        if session_id not in g.decision_tree.conversations:
            g.decision_tree.start_session(session_id, chat_mode=True)
            server_logging.add_server_log("triage", f"[DTREE] NEW SESSION STARTED: {session_id}", level="info", details={
                "session_id": session_id,
                "initial_node": "start",
                "timestamp": datetime.now().isoformat()
            })
            # Send initial UI reload signal for left sidebar
            yield f"data: {json.dumps({'type': 'session_started', 'session_id': session_id, 'reload_left_ui': True, 'call_status_api': True})}\n\n"

        # Get current node info from decision tree
        state = g.decision_tree.conversations[session_id]
        current_node = g.decision_tree.nodes[state.current_node_id]

        with mcp_manager.get_active_context():
            server_logging.add_server_log("MCP", f"MCP CONTEXT ACQUIRED: {session_id}", level="info")

            agent = get_or_create_session_agent(session_id, model_id)

            server_logging.add_server_log("Agent", f"[AGENT] AGENT ACQUIRED: {session_id}", level="info", details={
                "session_id": session_id,
                "agent_type": type(agent).__name__,
                "has_tools": hasattr(agent, 'tools'),
                "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0
            })
            
            # Dynamic next node selection based on decision tree structure
            def get_next_node_options(current_node, user_message):
                """Determine possible next nodes based on current node structure and user input"""
                if current_node.children:
                    return current_node.children[0]  # Always go to first child
                return current_node.id  # No children, stay here
            
            next_node_candidate = get_next_node_options(current_node, message)

            # Minimal prompt - just pass user message
            unified_prompt = message
            
            accumulated_response = ""

            server_logging.add_server_log("triage", f"[AGENT] STARTING LLM STREAM: {session_id}", level="info", details={
                "session_id": session_id,
                "prompt_length": len(unified_prompt),
                "agent_tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
                "next_node_candidate": str(next_node_candidate)
            })
            
            # Simplified Strands streaming - process events as they come
            tools_called = []  # Decision 5: Track tools called for finish logging
            try:
                async for event in agent.stream_async(unified_prompt):
                    if "data" in event:
                        text_data = event["data"]
                        accumulated_response += text_data

                        # Send all text - let frontend handle filtering
                        if text_data.strip():
                            yield f"data: {json.dumps({'type': 'content', 'content': text_data})}\n\n"

                    elif "current_tool_use" in event and event["current_tool_use"].get("name"):
                        tool_name = event["current_tool_use"]["name"]
                        tool_input = event["current_tool_use"].get("input", {})

                        # Decision 5: Enhanced tool call logging
                        server_logging.add_server_log("triage", f"[AGENT] TOOL IDENTIFIED: {tool_name}", level="info", details={
                            "session_id": session_id,
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                            "timestamp": datetime.now().isoformat()
                        })

                        mcp_server_name = mcp_manager.get_server_for_tool(tool_name)

                        server_logging.add_server_log("triage", f"[AGENT] MCP SERVER IDENTIFIED: {mcp_server_name}", level="info", details={
                            "session_id": session_id,
                            "mcp_server": mcp_server_name,
                            "tool_name": tool_name
                        })

                        server_logging.add_server_log("triage", f"[AGENT] TOOL EXECUTING: {mcp_server_name} -> {tool_name}", level="warning", details={
                            "session_id": session_id,
                            "mcp_server": mcp_server_name,
                            "tool_name": tool_name,
                            "timestamp": datetime.now().isoformat()
                        })

                        # Track for finish logging
                        tools_called.append(f"{mcp_server_name} -> {tool_name}")

                        yield f"data: {json.dumps({'type': 'tool_use', 'tool_name': tool_name, 'mcp_server': mcp_server_name})}\n\n"

                # Decision 5: Log tool completion summary
                if tools_called:
                    server_logging.add_server_log("triage", f"[AGENT] TOOLS FINISHED: {len(tools_called)} tool(s) executed", level="info", details={
                        "session_id": session_id,
                        "tools_called": tools_called,
                        "timestamp": datetime.now().isoformat()
                    })

                server_logging.add_server_log("triage", f"[AGENT] STREAM COMPLETE: {session_id}", level="info")

            except Exception as llm_error:
                server_logging.add_server_log("triage", f"[AGENT] LLM STREAM ERROR: {session_id} - {str(llm_error)}", level="error")
                yield f"data: {json.dumps({'type': 'content', 'content': 'An internal error occurred.'})}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        http_logging.logger.error(f"Error in chat stream: {str(e)}")
        yield f"data: {json.dumps({'type': 'content', 'content': 'An internal error occurred.'})}\n\n"
        yield "data: [DONE]\n\n"

async def stream_plain_response(message: str, model_id: str):
    """A very simple streaming response for basic checks"""
    server_logging.add_server_log("system", f"Starting plain text streaming for: {message[:50]}...")
    
    try:
        # Create simple Strands agent
        model = BedrockModel(
            model_id=model_id,
            temperature=0.7
        )
        
        # Get tools from MCP manager
        tools = mcp_manager.get_all_tools(active_only=True)
        
        agent = Agent(
            model=model,
            system_prompt="You are a helpful AI assistant. Use available tools when needed to answer user questions.",
            tools=tools
        )
        
        with mcp_manager.get_active_context():
            # Execute agent and get response
            response = agent(message)
            response_text = str(response)
            
            # Stream response in chunks
            chunk_size = 40
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i+chunk_size]
                yield chunk
                await asyncio.sleep(0.08)  # Small delay for streaming effect
                
    except Exception as e:
        error_msg = "An internal error occurred."
        server_logging.add_server_log("system", f"Plain text streaming error: {str(e)[:50]}...")
        yield error_msg

