"""Test to demonstrate the context issue"""
import asyncio
import boto3
import httpx
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient
from strands import Agent
from strands.models import BedrockModel

runtime_name = "mcpe2e_e2e-bm14m2AQY9"
region = "us-east-1"
user_pool_id = "us-east-1_IsYqleAY1"
client_id = "6i47v4nd15s0rfr07k4c4n9k1u"

def get_bearer_token():
    """Get Cognito bearer token"""
    cognito_client = boto3.client("cognito-idp", region_name=region)

    auth_response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": "kevin@datamond.ai",
            "PASSWORD": "NewStrongPassw0rd!2026",
        },
    )

    return auth_response["AuthenticationResult"]["AccessToken"]

def create_mcp_client(bearer_token):
    """Create MCP client"""
    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_name}/invocations?qualifier=DEFAULT&accountId={account_id}"

    def agentcore_transport():
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

async def test_wrong_way():
    """This demonstrates the WRONG way - listing tools in one context, using in another"""
    print("\n" + "="*60)
    print("TEST 1: WRONG WAY - Different contexts")
    print("="*60)

    bearer_token = get_bearer_token()
    mcp_client = create_mcp_client(bearer_token)

    # WRONG: List tools in one context
    print("Step 1: Listing tools in first context...")
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        print(f"  Found {len(tools)} tools")

    # Context is now CLOSED
    print("Step 2: Creating agent with those tools...")
    model = BedrockModel(model_id="us.amazon.nova-pro-v1:0", temperature=0.7)
    agent = Agent(model=model, system_prompt="You are helpful", tools=tools)

    # WRONG: Try to use tools in a DIFFERENT context
    print("Step 3: Trying to use tools in second context...")
    try:
        with mcp_client:
            async for event in agent.stream_async("Get balance for kevin@datamond.ai"):
                if "data" in event:
                    print(f"  Response: {event['data']}")
            print(f"  SUCCESS!")
    except Exception as e:
        print(f"  FAILED: {str(e)}")

async def test_right_way():
    """This demonstrates the RIGHT way - same context for list and use"""
    print("\n" + "="*60)
    print("TEST 2: RIGHT WAY - Same context")
    print("="*60)

    bearer_token = get_bearer_token()
    mcp_client = create_mcp_client(bearer_token)

    # RIGHT: Use the SAME context for everything
    print("Step 1: Entering context...")
    with mcp_client:
        print("Step 2: Listing tools in this context...")
        tools = mcp_client.list_tools_sync()
        print(f"  Found {len(tools)} tools")

        print("Step 3: Creating agent with those tools...")
        model = BedrockModel(model_id="us.amazon.nova-pro-v1:0", temperature=0.7)
        agent = Agent(model=model, system_prompt="You are helpful", tools=tools)

        print("Step 4: Using tools in SAME context...")
        try:
            async for event in agent.stream_async("Get balance for kevin@datamond.ai"):
                if "data" in event:
                    print(f"  Response: {event['data']}")
            print(f"  SUCCESS!")
        except Exception as e:
            print(f"  FAILED: {str(e)}")

if __name__ == "__main__":
    print("\nDemonstrating MCP Context Issue")
    print("================================\n")

    asyncio.run(test_wrong_way())
    asyncio.run(test_right_way())
