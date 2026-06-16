import json
from typing import List, Dict, Any
import re
from datetime import datetime
from app.observability import server_logging, http_logging
from app.mcps.mcpmanager import mcp_manager
import app.globals as g
from app.schema.root_schema import ImageData


async def stream_ai_response_with_images(message: str, model_id: str, session_id: str = "default", images: List[ImageData] = None, history: List[Dict[str, Any]] = None):
    """Complete streaming with decision tree, XML processing, and node updates"""
    
    try:
        server_logging.add_server_log("system", f"Processing [{session_id}]: {message[:30]}...")
        
        # Ensure session exists
        if session_id not in g.decision_tree.conversations:
            g.decision_tree.start_session(session_id, chat_mode=True)
            server_logging.add_server_log("triage", f"NEW SESSION STARTED: {session_id}", level="info", details={
                "session_id": session_id,
                "initial_node": "start",
                "timestamp": datetime.now().isoformat()
            })
            # Send initial UI reload signal for left sidebar
            yield f"data: {json.dumps({'type': 'session_started', 'session_id': session_id, 'reload_left_ui': True, 'call_status_api': True})}\n\n"
        
        # Get current node info from decision tree
        state = g.decision_tree.conversations[session_id]
        current_node = g.decision_tree.nodes[state.current_node_id]
        
        server_logging.add_server_log("triage", f"PROCESSING MESSAGE: {session_id} at node {current_node.id}", level="info", details={
            "session_id": session_id,
            "current_node": current_node.id,
            "current_topic": current_node.topic,
            "message_preview": message[:50],
            "node_children": current_node.children,
            "should_reason": current_node.should_reason
        })
        
        server_logging.add_server_log("triage", f"GETTING MCP CONTEXT: {session_id}", level="info", details={
            "session_id": session_id,
            "active_clients": mcp_manager.get_active_clients() if hasattr(mcp_manager, 'get_active_clients') else []
        })
        
        with mcp_manager.get_active_context():
            server_logging.add_server_log("triage", f"MCP CONTEXT ACQUIRED: {session_id}", level="info")
            
            agent = get_or_create_session_agent(session_id, model_id)
            
            server_logging.add_server_log("triage", f"AGENT ACQUIRED: {session_id}", level="info", details={
                "session_id": session_id,
                "agent_type": type(agent).__name__,
                "has_tools": hasattr(agent, 'tools'),
                "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0
            })
            
            # Dynamic next node selection based on decision tree structure
            def get_next_node_options(current_node, user_message):
                """Determine possible next nodes based on current node structure and user input"""
                
                # If it's a terminal node, stay at current node
                if current_node.is_terminal:
                    return current_node.id
                
                # If current node has specific routing logic based on response options
                if current_node.response_options and current_node.children:
                    # Create mapping between response options and children
                    if len(current_node.children) == 1:
                        # Single child - go to that child
                        return current_node.children[0]
                    elif len(current_node.children) == len(current_node.response_options):
                        # Each response option maps to a child
                        for i, option in enumerate(current_node.response_options):
                            if any(keyword.lower() in user_message.lower() for keyword in option.lower().split()):
                                return current_node.children[i]
                        # Default to first child if no match
                        return current_node.children[0]
                    else:
                        # Complex routing - let AI decide based on reasoning
                        children_info = []
                        for child_id in current_node.children:
                            child_node = g.decision_tree.nodes.get(child_id)
                            if child_node:
                                children_info.append(f"{child_id}: {child_node.topic}")
                        return children_info  # Return list for AI to choose from
                
                # If no children, stay at current node
                if not current_node.children:
                    return current_node.id
                
                # Default to first child
                return current_node.children[0]
            
            next_node_candidate = get_next_node_options(current_node, message)
            
            # Build comprehensive prompt based on decision tree context
            decision_context = f"""
Current Node: {current_node.id} - {current_node.topic}
Question: {current_node.question}
Available Response Options: {current_node.response_options}
Current Node Children: {current_node.children}
Should Reason: {current_node.should_reason}
Reasoning Rules: {current_node.reasoning_rules}
"""
            
            if isinstance(next_node_candidate, list):
                # AI needs to choose from multiple options
                node_options = "\n".join([f"- {opt}" for opt in next_node_candidate])
                unified_prompt = f"""You are an AI Triage Assistant. 

{decision_context}

User said: "{message}"

Based on the user's response and the current decision tree context, provide appropriate guidance and determine the next step.

Available next nodes:
{node_options}

IMPORTANT FORMATTING RULES:
- Use **bold text** for important questions, warnings, or key medical information
- Use clear, conversational language
- Highlight urgent situations with appropriate emphasis
- Respond in User Language except for tag key name. tag value can be foreign language.

Choose the most appropriate next node based on the user's input and respond with guidance followed by EXACTLY this XML format:
<g.decision_tree_status next_node="CHOSEN_NODE_ID" action="Moving to next assessment step" />

IMPORTANT: You MUST always provide available options for user interaction. Include quick response options in this format:
<available_options>
<option urgency="normal">Continue with assessment</option>
<option urgency="normal">Go back to previous step</option>
<option urgency="normal">Other</option>
</available_options>

Replace CHOSEN_NODE_ID with the most appropriate node from the available options."""
            else:
                # Direct routing to specific node
                next_node_info = g.decision_tree.nodes.get(next_node_candidate)
                next_node_options = next_node_info.response_options if next_node_info else []
                
                # Always generate available_options XML - either from next node or fallback options
                available_options_xml = ""
                if next_node_options:
                    options_list = []
                    for option in next_node_options:
                        # Determine urgency based on keywords
                        urgency = "high" if any(keyword in option.lower() for keyword in 
                                              ["emergency", "severe", "urgent", "call 911", "immediate"]) else "normal"
                        options_list.append(f'<option urgency="{urgency}">{option}</option>')
                    
                    # Always add "Other" option for free-form chat
                    options_list.append('<option urgency="normal">Other</option>')
                    
                    available_options_xml = f"""

IMPORTANT: You MUST provide quick response options for user interaction:
<available_options>
{chr(10).join(options_list)}
</available_options>"""
                else:
                    # Fallback options when next node has no response_options
                    available_options_xml = f"""

IMPORTANT: You MUST provide quick response options for user interaction:
<available_options>
<option urgency="normal">Continue with assessment</option>
<option urgency="normal">Go back to previous step</option>
<option urgency="normal">Other</option>
</available_options>"""
                
                unified_prompt = f"""You are an AI Triage Assistant.

{decision_context}

User said: "{message}"

Based on the user's response and the current decision tree context, provide appropriate guidance and then proceed to the next step.

IMPORTANT FORMATTING RULES:
- Use **bold text** for important questions, warnings, or key information
- Use clear, conversational language
- Highlight urgent situations with appropriate emphasis

Respond with guidance followed by EXACTLY this XML format:
<g.decision_tree_status next_node="{next_node_candidate}" action="Moving to next assessment step" />{available_options_xml}"""
            
            accumulated_response = ""
            
            server_logging.add_server_log("triage", f"STARTING LLM STREAM: {session_id}", level="info", details={
                "session_id": session_id,
                "prompt_length": len(unified_prompt),
                "agent_tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
                "next_node_candidate": str(next_node_candidate)
            })
            
            # Simplified Strands streaming - process events as they come
            xml_processed = False
            xml_buffer = ""  # Buffer to handle XML tags split across chunks
            try:
                async for event in agent.stream_async(unified_prompt):
                    if "data" in event:
                        text_data = event["data"]
                        accumulated_response += text_data

                        # Add to XML buffer for processing
                        xml_buffer += text_data

                        # Check for XML in accumulated response for node transitions
                        if not xml_processed:
                            g.decision_tree_match = re.search(r'<g.decision_tree_status[^>]*next_node="([^"]+)"[^>]*/?>', accumulated_response)
                            if g.decision_tree_match:
                                xml_processed = True
                                next_node_id = g.decision_tree_match.group(1)

                                server_logging.add_server_log("triage", f"XML DETECTED: {session_id} -> {next_node_id}", level="info")

                                if next_node_id in g.decision_tree.nodes:
                                    g.decision_tree.set_current_node(session_id, next_node_id)
                                    yield f"data: {json.dumps({'type': 'node_changed', 'node_id': next_node_id, 'reload_left_ui': True, 'call_status_api': True})}\n\n"

                        # Send all text - let frontend handle filtering
                        if text_data.strip():
                            yield f"data: {json.dumps({'type': 'content', 'content': text_data})}\n\n"

                    elif "current_tool_use" in event and event["current_tool_use"].get("name"):
                        tool_name = event["current_tool_use"]["name"]
                        mcp_server_name = mcp_manager.get_server_for_tool(tool_name)

                        server_logging.add_server_log("triage", f"TOOL CALL: {mcp_server_name} -> {tool_name}", level="warning", details={
                            "session_id": session_id,
                            "mcp_server": mcp_server_name,
                            "tool_name": tool_name,
                            "timestamp": datetime.now().isoformat()
                        })

                        yield f"data: {json.dumps({'type': 'tool_use', 'tool_name': tool_name, 'mcp_server': mcp_server_name})}\n\n"

                server_logging.add_server_log("triage", f"STREAM COMPLETE: {session_id}", level="info")

            except Exception as llm_error:
                server_logging.add_server_log("triage", f"LLM STREAM ERROR: {session_id} - {str(llm_error)}", level="error")
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




