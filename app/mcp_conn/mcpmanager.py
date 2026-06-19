"""
MCP Client Manager for Strands Agents
Based on Strands official documentation examples
"""

import os
import logging
import boto3
import httpx
from contextlib import contextmanager, ExitStack
from typing import Dict, List, Optional, Any
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

logger = logging.getLogger(__name__)


class MCPClientManager:
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.active_clients: List[str] = []

    def add_client(self, name: str, client: MCPClient):
        """Add an MCP client"""
        self.clients[name] = client
        if name not in self.active_clients:
            self.active_clients.append(name)
        logger.info(f"Added MCP client: {name}")

    def remove_client(self, name: str):
        """Remove an MCP client"""
        if name in self.clients:
            del self.clients[name]
        if name in self.active_clients:
            self.active_clients.remove(name)
        logger.info(f"Removed MCP client: {name}")

    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get a specific MCP client"""
        return self.clients.get(name)

    def get_active_clients(self) -> List[str]:
        """Get list of active client names"""
        return self.active_clients.copy()

    def set_client_active(self, name: str, active: bool):
        """Set a client as active or inactive"""
        if name in self.clients:
            if active and name not in self.active_clients:
                self.active_clients.append(name)
                logger.info(f"Activated MCP client: {name}")
            elif not active and name in self.active_clients:
                self.active_clients.remove(name)
                logger.info(f"Deactivated MCP client: {name}")
        else:
            logger.warning(f"Client {name} not found")

    def initialize_default_clients(self):
        """Initialize default MCP clients from config"""
        try:
            from .mcp_config import MCP_SERVERS

            # Clear existing clients
            self.clients.clear()
            self.active_clients.clear()

            servers_config = MCP_SERVERS

            for server_name, server_config in servers_config.items():
                try:
                    transport = server_config.get("transport", "agentcore")

                    if transport != "agentcore":
                        logger.warning(f"Skipping {server_name}: unsupported transport '{transport}'")
                        continue

                    # Create AgentCore HTTP transport MCP client
                    runtime_name = server_config.get("runtime_name")
                    region = server_config.get("region", "us-east-1")

                    # Get Cognito credentials
                    cognito_username = server_config.get("cognito_username")
                    cognito_password = server_config.get("cognito_password")
                    cognito_client_id = server_config.get("cognito_client_id")

                    if not all([runtime_name, cognito_username, cognito_password, cognito_client_id]):
                        logger.warning(f"Skipping {server_name}: missing AgentCore config fields")
                        continue

                    # Get bearer token from Cognito
                    try:
                        cognito_client = boto3.client("cognito-idp", region_name=region)
                        auth_response = cognito_client.initiate_auth(
                            ClientId=cognito_client_id,
                            AuthFlow="USER_PASSWORD_AUTH",
                            AuthParameters={
                                "USERNAME": cognito_username,
                                "PASSWORD": cognito_password,
                            },
                        )
                        bearer_token = auth_response["AuthenticationResult"]["AccessToken"]
                        logger.info(f"AgentCore auth successful for {server_name}")
                    except Exception as e:
                        logger.error(f"AgentCore auth failed for {server_name}: {str(e)}")
                        continue

                    # Build MCP URL
                    sts = boto3.client("sts")
                    account_id = sts.get_caller_identity()["Account"]
                    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_name}/invocations?qualifier=DEFAULT&accountId={account_id}"

                    # Create transport factory with captured variables
                    def create_agentcore_transport(url=mcp_url, token=bearer_token):
                        headers = {
                            "authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        }
                        http_client = httpx.AsyncClient(headers=headers, timeout=120.0)
                        return streamable_http_client(
                            url,
                            http_client=http_client,
                            terminate_on_close=False
                        )

                    mcp_client = MCPClient(create_agentcore_transport)

                    self.add_client(server_name, mcp_client)

                    # Set active state based on config
                    enabled = server_config.get("enabled", True)
                    if not enabled and server_name in self.active_clients:
                        self.active_clients.remove(server_name)

                    logger.info(
                        f"Initialized AgentCore MCP client: {server_name} (enabled={enabled})"
                    )

                except Exception as e:
                    logger.error(f"Failed to initialize MCP client {server_name}: {str(e)}")

            logger.info(f"Active MCP clients: {self.active_clients}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP clients: {str(e)}")

    def get_all_tools(self, active_only: bool = True) -> List[Any]:
        """Get all tools from active MCP clients"""
        all_tools = []

        clients_to_use = (
            self.active_clients if active_only else list(self.clients.keys())
        )

        for client_name in clients_to_use:
            if client_name not in self.clients:
                continue

            client = self.clients[client_name]

            try:
                # Use client in context to get tools (Strands way)
                with client:
                    tools = client.list_tools_sync()
                    if tools:
                        all_tools.extend(tools)
                        logger.info(f"Loaded {len(tools)} tools from {client_name}")
            except Exception as e:
                logger.error(f"Error loading tools from {client_name}: {str(e)}")

        return all_tools

    @contextmanager
    def get_active_context(self):
        """Get context manager for all active MCP clients"""
        # Use ExitStack to manage multiple context managers
        with ExitStack() as stack:
            contexts = []

            for client_name in self.active_clients:
                if client_name in self.clients:
                    try:
                        # Enter context for each client
                        stack.enter_context(self.clients[client_name])
                        contexts.append(client_name)
                    except Exception as e:
                        logger.error(f"Failed to enter context for {client_name}: {str(e)}")

            logger.info(f"Entering context with active clients: {contexts}")
            yield contexts


# Global instance
mcp_manager = MCPClientManager()
