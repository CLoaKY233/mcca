import asyncio
import json
import os
import sys
from typing import Optional, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.server_name = None

    async def connect_to_server_from_config(self, config_path: str, server_name: str):
        """Connect to an MCP server using configuration

        Args:
            config_path: Path to the configuration JSON file
            server_name: Name of the server in the config to connect to
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading config file: {str(e)}")
        
        # Check if the server exists in the config
        if "context_servers" not in config or server_name not in config["context_servers"]:
            raise ValueError(f"Server '{server_name}' not found in config")
        
        self.server_name = server_name
        server_config = config["context_servers"][server_name]
        
        # Extract command details
        if "command" not in server_config:
            raise ValueError(f"Server '{server_name}' does not have command configuration")
            
        cmd_config = server_config["command"]
        command_path = cmd_config.get("path")
        args = cmd_config.get("args", [])
        env = cmd_config.get("env", {})
        
        # Convert env dict to proper environment variables
        environment = os.environ.copy()
        if env:
            # Make sure all paths use correct format for the platform
            normalized_env = {}
            for key, value in env.items():
                if isinstance(value, str) and os.path.sep in value:
                    normalized_env[key] = os.path.normpath(value)
                else:
                    normalized_env[key] = value
            
            environment.update(normalized_env)
            print(f"Adding environment variables for server '{server_name}':")
            for key, value in normalized_env.items():
                print(f"  {key}={value}")
        
        # Debug the environment variables
        print("\nFull environment variables that will be passed to the process:")
        for key, value in sorted(environment.items()):
            if key.startswith("MIST_"):
                print(f"  {key}={value}")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command=command_path,
            args=args,
            env=environment
        )

        print(f"Connecting to server '{server_name}' with command: {command_path} {' '.join(args)}")
        
        # Connect to the server
        try:
            print("Establishing connection to server...")
            print(f"Command: {command_path}")
            print(f"Args: {args}")
            
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            print("Connection established, creating session...")
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            print("Initializing session...")
            await self.session.initialize()
            print("Session initialized successfully")
        except Exception as e:
            print(f"Error connecting to server: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print(f"\nConnected to server '{server_name}' with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                if hasattr(content, 'text') and content.text:
                    messages.append({
                      "role": "assistant",
                      "content": content.text
                    })
                messages.append({
                    "role": "user",
                    "content": result.content
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print(f"Connected to server: {self.server_name}")
        print("Type your queries or 'quit' to exit.")
        print("Type 'debug' to print diagnostic information.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break
                    
                if query.lower() == 'debug':
                    # Print diagnostic information
                    print("\n--- Diagnostic Information ---")
                    print(f"Server name: {self.server_name}")
                    print(f"Session active: {self.session is not None}")
                    if self.session:
                        tools = await self.session.list_tools()
                        print(f"Available tools: {[tool.name for tool in tools.tools]}")
                    continue

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 3:
        print("Usage: python client.py <config_file_path> <server_name>")
        sys.exit(1)

    config_path = sys.argv[1]
    server_name = sys.argv[2]
    
    print(f"Starting MCP client with config: {config_path}, server: {server_name}")
    
    client = MCPClient()
    try:
        await client.connect_to_server_from_config(config_path, server_name)
        await client.chat_loop()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up resources...")
        await client.cleanup()
        print("Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())