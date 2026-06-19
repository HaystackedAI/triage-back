import os
from app.observability import server_logging, http_logging
import app.globals as g
from .mcp_config import MCP_SERVERS

# setup_mcp_servers() removed - duplicate of mcpmanager.initialize_default_clients()


def load_mcp_config():
    """Load MCP configuration from mcp_config.py"""
    if g.mcp_servers:  # Already loaded
        return g.mcp_servers

    try:
        # Transform config to our internal format
        g.mcp_servers = {}

        for server_name, server_config in MCP_SERVERS.items():
            g.mcp_servers[server_name] = {
                "name": server_config.get("name", server_name.replace('_', ' ').title()),
                "enabled": server_config.get("enabled", True),
                "description": server_config.get("description", f"{server_name.replace('_', ' ').title()} MCP server"),
                "status": "ready" if server_config.get("enabled", True) else "disabled",
                "command": server_config.get("command", ""),
                "args": server_config.get("args", []),
                "env": server_config.get("env", {}),
                "transport": server_config.get("transport", "stdio"),
                "runtime_arn": server_config.get("runtime_arn", ""),
                "region": server_config.get("region", "")
            }

        server_logging.add_server_log("system", f"Loaded {len(g.mcp_servers)} MCP servers")
        return g.mcp_servers

    except Exception as e:
        http_logging.log_error(f"Error loading MCP config: {str(e)}")
        server_logging.add_server_log("system", f"Error loading MCP config: {str(e)}")
        return {}

def save_mcp_config(servers_config):
    """Save MCP configuration to mcp_config.py file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'mcp_config.py')

        # Build the new config dict
        updated_servers = {}
        for server_name, server_info in servers_config.items():
            # Preserve original config structure
            server_dict = {}

            # Core fields
            if server_info.get("transport"):
                server_dict["transport"] = server_info["transport"]

            # AgentCore fields
            if server_info.get("runtime_arn"):
                server_dict["runtime_arn"] = server_info["runtime_arn"]
            if server_info.get("region"):
                server_dict["region"] = server_info["region"]

            # Stdio fields
            if server_info.get("command"):
                server_dict["command"] = server_info["command"]
            if server_info.get("args"):
                server_dict["args"] = server_info["args"]
            if server_info.get("description"):
                server_dict["description"] = server_info["description"]

            # Always include enabled state
            server_dict["enabled"] = server_info.get("enabled", True)

            updated_servers[server_name] = server_dict

        # Write the Python file
        with open(config_path, 'w') as f:
            f.write('"""MCP Server Configuration\n\n')
            f.write('This module defines all MCP server configurations.\n')
            f.write('Imported directly instead of reading from JSON file for better type safety and performance.\n')
            f.write('"""\n\n')
            f.write('MCP_SERVERS = ')

            # Write dict with proper formatting
            import pprint
            formatted = pprint.pformat(updated_servers, indent=4, width=100)
            f.write(formatted)
            f.write('\n')

        server_logging.add_server_log("system", "Configuration saved to mcp_config.py")

    except Exception as e:
        http_logging.log_error(f"Error saving MCP config: {str(e)}")
        server_logging.add_server_log("system", f"Error saving config: {str(e)}")


# Load MCP servers from configuration at startup
load_mcp_config()

# initialize_mcp_servers() removed - use mcp_manager.initialize_default_clients() instead
