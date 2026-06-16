from datetime import datetime
from typing import Dict, List
import app.globals as g
def get_session_messages_for_ui(session_id: str, model_id: str) -> List[Dict]:
    """Get session messages formatted for UI from the actual agent"""
    agent_key = f"{session_id}:{model_id}"
    
    if agent_key not in g.session_agents:
        return []
    
    agent = g.session_agents[agent_key]
    
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

