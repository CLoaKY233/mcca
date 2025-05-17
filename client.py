import asyncio
import json
import os
import sys
import re
import traceback
from typing import Optional, Dict, Any, List, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # No API key needed for Ollama
        self.server_name = None
        # Get model name from environment or use default
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "llama3-groq-tool-use:8b")
        # Get host from environment if specified
        self.ollama_host = os.environ.get("OLLAMA_HOST", None)

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
            print(f"🔧 Adding environment variables for server '{server_name}':")
            for key, value in normalized_env.items():
                print(f"  {key}={value}")

        # Debug the environment variables - only in debug mode
        if os.environ.get("MCP_DEBUG"):
            print("\n🔍 Environment variables being passed to the process:")
            for key, value in sorted(environment.items()):
                if key.startswith("MIST_"):
                    print(f"  {key}={value}")

        # Create server parameters
        server_params = StdioServerParameters(
            command=command_path,
            args=args,
            env=environment
        )

        print(f"🔄 Connecting to server '{server_name}' with command: {command_path} {' '.join(args)}")

        # Connect to the server
        try:
            print("⏳ Establishing connection to server...")
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            print("✓ Connection established, creating session...")
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            print("⏳ Initializing session...")
            await self.session.initialize()
            print("✓ Session initialized successfully")
        except Exception as e:
            print(f"❌ Error connecting to server: {str(e)}")
            traceback.print_exc()
            raise

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools

        # Format tool list for better readability
        tool_names = [tool.name for tool in tools]
        print(f"\n🧰 Connected to server '{server_name}' with {len(tool_names)} tools available")

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        if not self.session:
            return "Error: Session not initialized"

        response = await self.session.list_tools()
        available_tools = response.tools

        # Store available_tools for later use
        self.available_tools = available_tools

        # Add instructions about available tools
        tool_info = "\n\nAvailable tools:\n"
        for tool in available_tools:
            tool_info += f"- {tool.name}: {tool.description}\n"
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                if "properties" in tool.inputSchema:
                    tool_info += "  Parameters:\n"
                    for param_name, param_details in tool.inputSchema["properties"].items():
                        tool_info += f"    - {param_name}: {param_details.get('description', '')}\n"

        # Add instructions for how to call tools
        tool_info += "\nTo call a tool, use this format in your response:\n"
        tool_info += "TOOL: tool_name\n"
        tool_info += "PARAMETERS: {\"param1\": \"value1\", \"param2\": \"value2\"}\n"

        # Prepare Ollama messages
        ollama_messages = []
        # Add initial user query with tool info
        initial_user_content = query + tool_info
        ollama_messages.append({"role": "user", "content": initial_user_content})

        # Process response and handle tool calls
        final_text = []

        try:
            # Send request to Ollama model
            # print(f"Sending request to Ollama model codellama:latest")
            # print(f"Messages: {json.dumps(ollama_messages, indent=2)}")

            # Use model name from environment variable
            ollama_kwargs = {"model": self.ollama_model, "messages": ollama_messages}
            # Add host if specified in environment
            if self.ollama_host:
                ollama_kwargs["host"] = self.ollama_host

            ollama_response = ollama.chat(**ollama_kwargs)

            response_text = ollama_response['message']['content']
            # print(f"Received response from Ollama: {response_text}")
            final_text.append(response_text)

            # Add assistant's response to message history for potential follow-up
            ollama_messages.append({"role": "assistant", "content": response_text})

            # Extract tool calls using regex pattern
            tool_calls = self._extract_tool_calls(response_text)
            # print(f"Extracted tool calls: {tool_calls}")

            # If we find tool calls, execute them
            for tool_name, tool_args in tool_calls:
                # Format tool call for display
                formatted_args = json.dumps(tool_args, indent=2)
                tool_call_display = f"\n🔧 Using tool: {tool_name}\n📝 Parameters: {formatted_args}"
                final_text.append(tool_call_display)

                try:
                    # print(f"Calling MCP tool: {tool_name} with args: {tool_args}")
                    result = await self.session.call_tool(tool_name, tool_args)
                    # print(f"Tool result: {result.content}")

                    # Format and add tool response to conversation
                    tool_result = str(result.content)
                    # Parse and format the content for better readability
                    if isinstance(result.content, str):
                        # Plain string - just display it
                        tool_result = result.content
                    else:
                        # Convert to string and handle special cases
                        tool_result = str(result.content)
                        # Replace escaped newlines with actual newlines
                        tool_result = tool_result.replace('\\n', '\n')
                        # Try to clean up any stringified list representation
                        tool_result = tool_result.replace("', '", "'\n'")

                    text_result = f"\n📊 Result:\n{tool_result}"
                    final_text.append(text_result)

                    # Add tool execution result to messages for follow-up
                    text_result_for_llm = f"Tool {tool_name} execution result: {tool_result}"
                    ollama_messages.append({"role": "user", "content": text_result_for_llm})

                    # Get follow-up response from Ollama
                    # print("Getting follow-up response from Ollama...")
                    # print(f"Follow-up messages: {json.dumps(ollama_messages, indent=2)}")

                    # Use model name from environment variable
                    ollama_kwargs = {"model": self.ollama_model, "messages": ollama_messages}
                    # Add host if specified in environment
                    if self.ollama_host:
                        ollama_kwargs["host"] = self.ollama_host

                    follow_up_response_data = ollama.chat(**ollama_kwargs)
                    follow_up_text = follow_up_response_data['message']['content']
                    final_text.append("\n" + follow_up_text)

                    # Add this follow-up to messages if further interaction is planned in this turn
                    ollama_messages.append({"role": "assistant", "content": follow_up_text})

                except Exception as e:
                    error_msg = f"\n❌ Error calling tool {tool_name} or getting follow-up: {str(e)}"
                    print(error_msg)
                    traceback.print_exc()
                    final_text.append(error_msg)
                    # Add error as context for the model if needed for a follow-up
                    ollama_messages.append({"role": "user", "content": f"Error during tool call for {tool_name}: {str(e)}"})

        except Exception as e:
            print(f"\n🛑 ERROR generating content with Ollama: {str(e)}")
            traceback.print_exc()
            final_text.append(f"Error generating content with Ollama: {str(e)}")

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n🚀 MCP Client Started!")
        print(f"🔗 Connected to server: {self.server_name}")
        print("💬 Type your queries or 'quit' to exit.")
        print("🛠️ Type 'debug' to print diagnostic information.")
        print("〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")

        while True:
            try:
                query = input("\n🔍 Query: ").strip()

                if query.lower() == 'quit':
                    break

                if query.lower() == 'debug':
                    # Print diagnostic information
                    print("\n📊 --- Diagnostic Information ---")
                    print(f"🔹 Server name: {self.server_name}")
                    print(f"🔹 Session active: {self.session is not None}")
                    if self.session:
                        tools = await self.session.list_tools()
                        print(f"🔹 Available tools: {[tool.name for tool in tools.tools]}")
                    print("〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")
                    continue

                print("\n⏳ Processing your query...")
                response = await self.process_query(query)

                # Print a separator before the response
                print("\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")
                print("🤖 Response:")
                print(response)
                print("〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️")

            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                traceback.print_exc()

    def _extract_tool_calls(self, text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Extract tool calls from text response

        Format expected:
        TOOL: tool_name
        PARAMETERS: {"param1": "value1", "param2": "value2"}
        """
        tool_calls = []

        # Look for the pattern TOOL: name followed by PARAMETERS: {...}
        tool_pattern = re.compile(r'TOOL:\s*([\w\-]+)\s*[\n\r]+\s*PARAMETERS:\s*({.*?})', re.DOTALL)

        matches = tool_pattern.findall(text)
        # Debug only
        # print(f"Regex matches found: {matches}")

        for tool_name, params_str in matches:
            try:
                # Try to parse the parameters as JSON
                # Remove any surrounding markdown backticks
                cleaned_params = params_str.strip('`').strip()
                # Debug only
                # print(f"Parsing parameters for {tool_name}: {cleaned_params}")
                params = json.loads(cleaned_params)
                tool_calls.append((tool_name.strip(), params))
            except json.JSONDecodeError as e:
                print(f"\n⚠️ Failed to parse parameters for tool {tool_name}: {params_str}")
                print(f"JSON parse error: {str(e)}")
                # If JSON parsing fails, add with empty params
                tool_calls.append((tool_name.strip(), {}))

        # Also look for a simpler pattern in case the model doesn't format correctly
        if not tool_calls and hasattr(self, 'available_tools'):
            for tool in self.available_tools:
                tool_mention = f"use the {tool.name} tool"
                if tool_mention.lower() in text.lower():
                    print(f"\nℹ️ Found simple tool mention: {tool.name}")
                    tool_calls.append((tool.name, {}))

        return tool_calls

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 3:
        print("Usage: python client.py <config_file_path> <server_name>")
        sys.exit(1)

    # Print Python version for debugging
    print(f"🐍 Python version: {sys.version}")

    config_path = sys.argv[1]
    server_name = sys.argv[2]

    print(f"🚀 Starting MCP client with config: {config_path}, server: {server_name}")
    # Display the model that will be used
    ollama_model = os.environ.get("OLLAMA_MODEL", "codellama:latest")
    print(f"🤖 Using Ollama with model: {ollama_model}")

    client = MCPClient()
    try:
        await client.connect_to_server_from_config(config_path, server_name)
        await client.chat_loop()
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up resources...")
        await client.cleanup()
        print("✓ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())
