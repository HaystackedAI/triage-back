"""Test get_balance tool on deployed MCP server"""
import asyncio
import sys
import boto3
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import httpx
import json

runtime_name = "mcpe2e_e2e-bm14m2AQY9"
region = "us-east-1"
user_pool_id = "us-east-1_IsYqleAY1"
client_id = "6i47v4nd15s0rfr07k4c4n9k1u"

sts = boto3.client("sts")
account_id = sts.get_caller_identity()["Account"]

mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_name}/invocations?qualifier=DEFAULT&accountId={account_id}"

async def test_get_balance(username, password, user_alias):
    """Call get_balance tool"""
    try:
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

                print(f"\nCalling get_balance for user: {user_alias}")
                print("=" * 50)

                result = await session.call_tool(
                    "get_balance",
                    arguments={"user_alias": user_alias}
                )

                print("\nResult:")
                print(json.dumps(result.model_dump(), indent=2))

                if hasattr(result, 'content'):
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            print("\nBalance Information:")
                            print(content_item.text)

                return True

    except Exception as e:
        print(f"\nTest FAILED: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        username = sys.argv[1]
        password = sys.argv[2]
        user_alias = sys.argv[3]
    else:
        print("Usage: python test_get_balance.py <username> <password> <user_alias>")
        print("Example: python test_get_balance.py kevin@datamond.ai password123 kevin@datamond.ai")
        sys.exit(1)

    result = asyncio.run(test_get_balance(username, password, user_alias))
    sys.exit(0 if result else 1)
