from datetime import datetime
from typing import Dict, List
import app.globals as g

def add_server_log(server_name: str, message: str, level: str = "info", details: Dict = None):
    """Add a structured log entry for a server"""
    timestamp = datetime.now().isoformat()
    
    # Create structured log entry
    log_entry = {
        "timestamp": timestamp,
        "server": server_name,
        "level": level,
        "message": message,
        "details": details or {}
    }
    
    if server_name not in g.server_logs:g.server_logs[server_name] = []

    # Prevent duplicate consecutive messages (but allow tool executions)
    if g.server_logs[server_name] and not message.startswith("Executing "):
        last_log = g.server_logs[server_name][-1]
        if isinstance(last_log, dict) and last_log.get("message") == message:
            return  # Skip duplicate message

    g.server_logs[server_name].append(log_entry)

    # Keep only last 50 logs per server
    if len(g.server_logs[server_name]) > 50:
        g.server_logs[server_name] = g.server_logs[server_name][-50:]
