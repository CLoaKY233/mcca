# mcpclient/session.py
from typing import Dict, Any, List, Optional
from mcp.types import Tool
from connectors.base import BaseConnector

class MCPSession:
    """Session manager for MCP connections"""

    def __init__(self, connector: BaseConnector):
        """Initialize a new MCP session

        Args:
            connector: The connector to use
        """
        self.connector = connector
        self.session_info: Optional[Dict[str, Any]] = None
        self.tools: List[Tool] = []

    async def __aenter__(self):
        """Enter the async context manager"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager"""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to the MCP implementation"""
        await self.connector.connect()

    async def disconnect(self) -> None:
        """Disconnect from the MCP implementation"""
        await self.connector.disconnect()

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session

        Returns:
            Session information
        """
        self.session_info = await self.connector.initialize()
        self.tools = self.connector.tools
        return self.session_info

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        return await self.connector.call_tool(name, arguments)

    @property
    def available_tools(self) -> List[Tool]:
        """Get available tools

        Returns:
            List of available tools
        """
        return self.tools
