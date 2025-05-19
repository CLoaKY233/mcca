import os
from typing import Dict, Any, Optional, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .base import BaseConnector

class StdioConnector(BaseConnector):
    """Connector for MCP implementations using stdio transport"""

    def __init__(self, command: str, args: list[str], env: Optional[Dict[str, Any]] = None):
        """Initialize a new stdio connector

        Args:
            command: Command to execute
            args: Command arguments
            env: Environment variables
        """
        super().__init__()
        self.command = command
        self.args = args
        self.env = env or {}
        self.exit_stack = AsyncExitStack()
        self.stdio = None
        self.write = None

    async def connect(self) -> ClientSession:
        """Connect to MCP implementation

        Returns:
            Initialized MCP client session
        """
        if self._connected:
            if self.session is None:
                raise RuntimeError("Connected but session is None")
            return self.session

        # Prepare environment variables
        environment = os.environ.copy()
        environment.update(self.env)

        # Create server parameters
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=environment
        )

        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        self._connected = True
        return self.session

    async def disconnect(self) -> None:
        """Disconnect from MCP implementation"""
        if not self._connected:
            return

        await self.exit_stack.aclose()
        self.session = None
        self.stdio = None
        self.write = None
        self._connected = False
