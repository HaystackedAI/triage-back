"""
Debug script to test MCP static server
Run this to verify MCP integration is working
"""

import asyncio
import sys
sys.path.insert(0, 'B:\\triage-back')

from app.mcp_conn.mcpmanager import mcp_manager

async def test_mcp_static():
    print("=" * 60)
    print("MCP STATIC SERVER DEBUG TEST")
    print("=" * 60)

    # Step 1: Initialize MCP clients
    print("\n[1] Initializing MCP clients...")
    mcp_manager.initialize_default_clients()

    # Step 2: Check active clients
    print(f"\n[2] Active clients: {mcp_manager.get_active_clients()}")

    # Step 3: Get all tools
    print("\n[3] Getting all tools...")
    tools = mcp_manager.get_all_tools(active_only=True)
    print(f"    Total tools found: {len(tools)}")

    # Step 4: List tools by server
    print("\n[4] Tools by server:")
    for client_name in mcp_manager.get_active_clients():
        client = mcp_manager.get_client(client_name)
        if client:
            try:
                with client:
                    client_tools = client.list_tools_sync()
                    print(f"    {client_name}: {len(client_tools)} tools")
                    for tool in client_tools:
                        print(f"      - {tool.name}: {tool.description}")
            except Exception as e:
                print(f"    {client_name}: ERROR - {e}")

    # Step 5: Test calling static tools
    print("\n[5] Testing static server tools...")
    static_client = mcp_manager.get_client("static")

    if static_client:
        try:
            with static_client:
                # Test read_some_value
                print("\n    Testing: read_some_value()")
                result = static_client.call_tool_sync("read_some_value", {})
                print(f"    ✓ Result: {result}")

                # Test write_value
                print("\n    Testing: write_value('Hello MCP!')")
                result = static_client.call_tool_sync("write_value", {"value": "Hello MCP!"})
                print(f"    ✓ Result: {result}")

        except Exception as e:
            print(f"    ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("    ✗ Static client not found!")

    print("\n" + "=" * 60)
    print("DEBUG TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mcp_static())
