import os,json
from app.observability import server_logging, http_logging
import app.globals as g

# setup_mcp_servers() removed - duplicate of mcpmanager.initialize_default_clients()


def load_mcp_config():
    """Load MCP configuration from mcp.json file"""
    if g.mcp_servers:  # Already loaded
        return g.mcp_servers
        
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'mcp.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Transform config to our internal format
        g.mcp_servers = {}
        
        # Check for both 'servers' and 'mcpServers' keys for compatibility
        servers_config = config.get('mcpServers', config.get('servers', {}))
        
        for server_name, server_config in servers_config.items():
            g.mcp_servers[server_name] = {
                "name": server_config.get("name", server_name.replace('_', ' ').title()),
                "enabled": server_config.get("enabled", True),
                "description": server_config.get("description", f"{server_name.replace('_', ' ').title()} MCP server"),
                "status": "ready" if server_config.get("enabled", True) else "disabled",
                "command": server_config.get("command", ""),
                "args": server_config.get("args", []),
                "env": server_config.get("env", {})
            }
        
        server_logging.add_server_log("system", f"Loaded {len(g.mcp_servers)} MCP servers")
        return g.mcp_servers
        
    except Exception as e:
        http_logging.log_error(f"Error loading MCP config: {str(e)}")
        server_logging.add_server_log("system", f"Error loading MCP config: {str(e)}")
        return {}

def save_mcp_config(servers_config):
    """Save MCP configuration to mcp.json file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'mcp.json')
        
        # Load existing config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get the correct servers key
        servers_key = 'mcpServers' if 'mcpServers' in config else 'servers'
        
        # Update server enabled states
        for server_name, server_info in servers_config.items():
            if server_name in config.get(servers_key, {}):
                config[servers_key][server_name]['enabled'] = server_info.get('enabled', True)
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        server_logging.add_server_log("system", "Configuration saved")
        
    except Exception as e:
        http_logging.log_error(f"Error saving MCP config: {str(e)}")
        server_logging.add_server_log("system", f"Error saving config: {str(e)}")


# Load MCP servers from configuration at startup
load_mcp_config()

# initialize_mcp_servers() removed - use mcp_manager.initialize_default_clients() instead
