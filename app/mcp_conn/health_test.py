# cd B:/mcp/mcpe2e/app/client
# python health_test.py "kevin@datamond.ai" "NewStrongPassw0rd!2026"
"""Minimal health check for deployed MCP server on AgentCore Runtime Works with public Cognito app clients (no client secret required)"""
import asyncio, sys, boto3, os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import httpx

# Runtime details
runtime_name = "mcpe2e_e2e-bm14m2AQY9"
region = "us-east-1"

user_pool_id = "us-east-1_IsYqleAY1"
client_id = "6i47v4nd15s0rfr07k4c4n9k1u"

# Get account ID
sts = boto3.client("sts")
account_id = sts.get_caller_identity()["Account"]

# Build MCP URL
mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_name}/invocations?qualifier=DEFAULT&accountId={account_id}"

print("Testing MCP server health")
print(f"Runtime: {runtime_name}")
print(f"URL: {mcp_url}\n")

async def health_check(username, password):
    """Simple health check - list available tools"""
    try:
        # Initialize Cognito client
        cognito_client = boto3.client("cognito-idp", region_name=region)

        # Authenticate using USER_PASSWORD_AUTH (no secret hash needed for public clients)
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

        headers = {
            "authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }

        print("Connecting to MCP server...")
        http_client = httpx.AsyncClient(headers=headers, timeout=120.0)
        async with streamable_http_client(
            mcp_url,
            http_client=http_client,
            terminate_on_close=False
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_result = await session.list_tools()

                print("Available MCP Tools:")
                print("=" * 50)
                for tool in tool_result.tools:
                    print(f"- {tool.name}: {tool.description}")

                print(f"\nTotal tools: {len(tool_result.tools)}")
                print("\nHealth check PASSED!")
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
        print("Usage: python health_test.py <username> <password>")
        print("\nOr enter credentials interactively:")
        username = input("Username: ")
        password = input("Password: ")

    result = asyncio.run(health_check(username, password))
    sys.exit(0 if result else 1)
