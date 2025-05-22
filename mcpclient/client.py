from typing import Dict, Any, List, Optional, AsyncGenerator
import traceback

from mcpclient.config import Config
from mcpclient.session import MCPSession
from mcpclient.connectors.stdio import StdioConnector
from mcpclient.tools.extraction import ToolExtractor
from mcpclient.tools.execution import ToolExecutor
from mcpclient.llm.gpt4o import GptLLM
from mcpclient.llm.gemini import GeminiLLM


class MCPClient:
    """Client for interacting with MCP servers"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new MCP client

        Args:
            config_path: Path to configuration file
            config_dict: Configuration dictionary
        """
        self.config = Config(config_path, config_dict)
        self.active_session: Optional[MCPSession] = None
        self.active_server_name: Optional[str] = None
        self.llm = GptLLM()

    async def connect_to_server(self, server_name: str) -> None:
        """Connect to a server

        Args:
            server_name: Name of server to connect to

        Raises:
            ValueError: If server not found or connection fails
        """
        try:
            # Get server configuration
            server_config = self.config.get_server_config(server_name)

            # Extract command details
            if "command" not in server_config:
                raise ValueError(
                    f"Server '{server_name}' does not have command configuration"
                )

            cmd_config = server_config["command"]
            command_path = cmd_config.get("path")
            args = cmd_config.get("args", [])
            env = cmd_config.get("env", {})

            # Normalize environment variables
            environment = self.config.normalize_env_variables(env)

            # Create connector
            connector = StdioConnector(command=command_path, args=args, env=environment)

            # Create and initialize session
            self.active_session = MCPSession(connector)
            await self.active_session.connect()
            await self.active_session.initialize()
            self.active_server_name = server_name

            print(
                f"✅ Connected to server '{server_name}' with {len(self.active_session.tools)} tools available"
            )

        except Exception as e:
            print(f"❌ Error connecting to server: {str(e)}")
            traceback.print_exc()
            raise

    def _format_tool_info(self, tools: List[Any]) -> str:
        """Format tool information for the LLM

        Args:
            tools: List of tools

        Returns:
            Formatted tool information
        """
        tool_info = "\n\nAvailable tools:\n"
        for tool in tools:
            tool_info += f"- {tool.name}: {tool.description}\n"
            if hasattr(tool, "inputSchema") and tool.inputSchema:
                if "properties" in tool.inputSchema:
                    tool_info += "  Parameters:\n"
                    for param_name, param_details in tool.inputSchema[
                        "properties"
                    ].items():
                        required = (
                            "required" in tool.inputSchema
                            and param_name in tool.inputSchema["required"]
                        )
                        req_tag = " (required)" if required else ""
                        tool_info += f"    - {param_name}{req_tag}: {param_details.get('description', '')}\n"

        # Add instructions for how to call tools
        tool_info += "\nTo call a tool, use this format in your response:\n"
        tool_info += "TOOL: tool_name\n"
        tool_info += 'PARAMETERS: {"param1": "value1", "param2": "value2"}\n'

        return tool_info

    async def process_query(self, query: str) -> str:
        """Process a query using the LLM and available tools

        Args:
            query: User query

        Returns:
            Generated response

        Raises:
            RuntimeError: If no active session
        """
        if not self.active_session:
            raise RuntimeError("No active session. Connect to a server first.")

        # Create initial messages
        messages = [{"role": "user", "content": query}]

        # Get tool information
        tools = self.active_session.available_tools
        tool_info = self._format_tool_info(tools)

        # Get initial response
        response_text = await self.llm.generate(messages, tool_info)

        # Extract tool calls
        tool_calls = ToolExtractor.extract_tool_calls(response_text, tools)

        # Build final response
        final_text = [response_text]

        # Process tool calls
        for tool_name, tool_args in tool_calls:
            # Format and add tool call to response
            formatted_args = str(tool_args)
            tool_call_display = (
                f"\n🔧 Using tool: {tool_name}\n📝 Parameters: {formatted_args}"
            )
            final_text.append(tool_call_display)

            try:
                # Execute tool
                result = await self.active_session.call_tool(tool_name, tool_args)

                # Format the result
                tool_result = str(result.content)
                result_display = f"\n📊 Result:\n{tool_result}"
                final_text.append(result_display)

                # Get follow-up response
                follow_up_messages = messages.copy()
                follow_up_messages.append({"role": "model", "content": response_text})
                follow_up_messages.append({"role": "user", "content": result_display})

                follow_up = await self.llm.generate(follow_up_messages)
                final_text.append("\n" + follow_up)

            except Exception as e:
                error_msg = f"\n❌ Error calling tool {tool_name}: {str(e)}"
                final_text.append(error_msg)

        return "\n".join(final_text)

    async def process_query_streaming(self, query: str) -> AsyncGenerator[str, None]:
        """Process a query with streaming response.

        Simple flow:
        1. User sends message
        2. LLM responds
        3. If response has tool call, execute tool
        4. Send tool result back to LLM
        5. Repeat 2-4 until no more tool calls

        Args:
            query: User query

        Yields:
            Response chunks
        """
        if not self.active_session:
            raise RuntimeError("No active session. Connect to a server first.")

        # Get available tools
        tools = self.active_session.available_tools
        tool_info = self._format_tool_info(tools)

        # Start with user message
        messages = [{"role": "user", "content": query}]

        # Maximum number of turns to prevent infinite loops
        max_turns = 10
        turn_count = 0

        while turn_count < max_turns:
            turn_count += 1

            # --- Get LLM Response ---
            llm_response = ""
            try:
                # Separate turns with visual indicator if not the first turn
                if turn_count > 1:
                    yield "\n\n"

                # Stream LLM response
                async for chunk in self.llm.generate_streaming(messages, tool_info if turn_count == 1 else None):
                    llm_response += chunk
                    yield chunk

            except Exception as e:
                yield f"\n\n❌ Error: {str(e)}\n"
                break

            # Add LLM response to conversation history
            messages.append({"role": "model", "content": llm_response})

            # --- Extract Tool Calls ---
            tool_calls = ToolExtractor.extract_tool_calls(llm_response, tools)

            # If no tool calls, we're done
            if not tool_calls:
                break

            # --- Execute Tools ---
            for tool_name, tool_args in tool_calls:
                # Format tool call for output
                yield f"\n\n🔧 Using tool: {tool_name}\n📝 Parameters: {str(tool_args)}"

                try:
                    # Execute the tool
                    result = await self.active_session.call_tool(tool_name, tool_args)

                    # Format and show result
                    result_text = ToolExecutor.format_tool_result(result)
                    yield f"\n📊 Result:\n{result_text}"

                    # Add tool result to conversation history as a user message
                    result_content = f"TOOL RESULT: {tool_name}\n{result_text}"
                    messages.append({"role": "user", "content": result_content})

                except Exception as e:
                    error_msg = f"\n❌ Error: {str(e)}"
                    yield error_msg

                    # Add error to conversation history
                    error_content = f"TOOL ERROR: {tool_name}\n{str(e)}"
                    messages.append({"role": "user", "content": error_content})

        # If we hit the max turn limit
        if turn_count >= max_turns:
            yield f"\n\n❌ Reached maximum number of turns ({max_turns})."

    async def get_available_servers(self) -> List[str]:
        """Get list of available servers

        Returns:
            List of server names
        """
        return self.config.get_server_names()

    async def disconnect(self) -> None:
        """Disconnect from the active server"""
        if self.active_session:
            await self.active_session.disconnect()
            self.active_session = None
            self.active_server_name = None
