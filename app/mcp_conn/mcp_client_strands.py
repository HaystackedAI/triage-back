"""
AgentCore MCP Client using Strands Framework
Demonstrates how to connect to AWS Bedrock AgentCore MCP runtimes using Strands MCPClient
"""
import asyncio
import sys
import boto3
import httpx
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

# Runtime details
runtime_name = "mcpe2e_e2e-bm14m2AQY9"
region = "us-east-1"

user_pool_id = "us-east-1_IsYqleAY1"
client_id = "6i47v4nd15s0rfr07k4c4n9k1u"


def get_agentcore_mcp_url(runtime_name: str, region: str) -> str:
    """Build the AgentCore MCP invocation URL"""
    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_name}/invocations?qualifier=DEFAULT&accountId={account_id}"


def get_cognito_bearer_token(username: str, password: str) -> str:
    """Authenticate with Cognito and get bearer token"""
    cognito_client = boto3.client("cognito-idp", region_name=region)

    print(f"Authenticating user: {username}...")
    auth_response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
    )

    bearer_token = auth_response["AuthenticationResult"]["AccessToken"]
    print("Authentication successful!\n")
    return bearer_token


def create_agentcore_mcp_client(mcp_url: str, bearer_token: str) -> MCPClient:
    """Create a Strands MCPClient for AgentCore runtime"""

    def agentcore_transport():
        """Transport factory for AgentCore HTTP connection"""
        headers = {
            "authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }
        http_client = httpx.AsyncClient(headers=headers, timeout=120.0)

        return streamable_http_client(
            mcp_url,
            http_client=http_client,
            terminate_on_close=False
        )

    return MCPClient(agentcore_transport)


async def health_check_strands(username: str, password: str):
    """Health check using Strands MCPClient"""
    try:
        # Get MCP URL
        mcp_url = get_agentcore_mcp_url(runtime_name, region)
        print("Testing MCP server health (Strands version)")
        print(f"Runtime: {runtime_name}")
        print(f"URL: {mcp_url}\n")

        # Authenticate
        bearer_token = get_cognito_bearer_token(username, password)

        # Create Strands MCPClient
        print("Creating Strands MCPClient...")
        mcp_client = create_agentcore_mcp_client(mcp_url, bearer_token)

        # Use client in context to get tools (Strands way)
        print("Connecting to MCP server...")
        with mcp_client:
            tools = mcp_client.list_tools_sync()

            print("Available MCP Tools:")
            print("=" * 50)
            for tool in tools:
                tool_name = getattr(tool, 'tool_name', getattr(tool, 'name', 'unknown'))
                description = getattr(tool, 'description', 'No description')
                print(f"- {tool_name}: {description}")

            print(f"\nTotal tools: {len(tools)}")
            print("\nHealth check PASSED!")
            print(f"Tool types: {[type(t).__name__ for t in tools[:3]]}")
            return True

    except Exception as e:
        print(f"\nHealth check FAILED: {e}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Get credentials from command line or prompt
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        print("Usage: python mcp_client_strands.py <username> <password>")
        print("\nOr enter credentials interactively:")
        username = input("Username: ")
        password = input("Password: ")

    result = asyncio.run(health_check_strands(username, password))
    sys.exit(0 if result else 1)
