# mcpclient/cli.py
import asyncio
import sys
import os
import traceback

from mcpclient.client import MCPClient

async def select_server(client):
    """Interactive server selection if multiple servers are available"""
    servers = await client.get_available_servers()

    if not servers:
        print("❌ No servers found in the configuration file.")
        return None

    if len(servers) == 1:
        # If there's only one server, select it automatically
        server_name = servers[0]
        print(f"🔄 Only one server available. Automatically selecting: {server_name}")
        return server_name

    # Multiple servers, let the user choose
    print("\nAvailable servers:")
    for i, name in enumerate(servers):
        print(f"{i+1}. {name}")

    while True:
        try:
            choice = input("\nSelect a server (number or name): ").strip()

            # Try to interpret as a number
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(servers):
                    return servers[idx]
                else:
                    print("❌ Invalid selection. Please choose a valid number.")
            except ValueError:
                # Not a number, try to match by name
                if choice in servers:
                    return choice
                else:
                    print("❌ Server not found. Please enter a valid server name or number.")
        except KeyboardInterrupt:
            return None

async def chat_loop(client):
    """Run an interactive chat loop"""
    print("\n🚀 MCP Client Started!")
    print(f"🔗 Connected to server: {client.active_server_name}")
    print("💬 Type your queries or 'quit' to exit.")
    print("🔄 Type 'servers' to list available servers.")
    print("🔌 Type 'connect <server_name>' to connect to a different server.")
    print("🛠️ Type 'debug' to print diagnostic information.")
    print("〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")

    while True:
        try:
            query = input("\n🔍 Query: ").strip()

            if query.lower() == 'quit':
                break

            if query.lower() == 'servers':
                servers = await client.get_available_servers()
                print("\nAvailable servers:")
                for i, name in enumerate(servers):
                    active = " (ACTIVE)" if name == client.active_server_name else ""
                    print(f"{i+1}. {name}{active}")
                continue

            if query.lower().startswith('connect '):
                server_name = query[8:].strip()
                print(f"\n⏳ Connecting to server '{server_name}'...")
                await client.disconnect()
                await client.connect_to_server(server_name)
                print(f"✅ Connected to server '{server_name}'")
                continue

            if query.lower() == 'debug':
                # Print diagnostic information
                print("\n📊 --- Diagnostic Information ---")
                print(f"🔹 Server name: {client.active_server_name}")
                print(f"🔹 Session active: {client.active_session is not None}")
                if client.active_session:
                    tools = client.active_session.available_tools
                    print(f"🔹 Available tools: {[tool.name for tool in tools]}")
                print("〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")
                continue

            print("\n⏳ Processing your query...")

            # Use streaming response processing
            print("\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")
            print("🤖 Response:")

            async for chunk in client.process_query_streaming(query):
                print(chunk, end="", flush=True)

            print("\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            traceback.print_exc()

async def main():
    # Make server_name optional
    if len(sys.argv) < 2:
        print("Usage: python cli.py <config_file_path> [server_name]")
        sys.exit(1)

    config_path = sys.argv[1]
    server_name = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"🚀 Starting MCP client with config: {config_path}")

    client = MCPClient(config_path)
    try:
        # If no server name provided, let user select or auto-select the only server
        if not server_name:
            server_name = await select_server(client)
            if not server_name:
                print("❌ No server selected. Exiting.")
                return

        print(f"⏳ Connecting to server: {server_name}")
        await client.connect_to_server(server_name)
        await chat_loop(client)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up resources...")
        await client.disconnect()
        print("✓ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())
