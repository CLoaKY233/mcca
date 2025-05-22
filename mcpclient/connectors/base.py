from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict, Union
from mcp import ClientSession
from mcp.types import Tool, InitializeResult


# Define a TypedDict for the initialize result if needed
class SessionInfo(TypedDict, total=False):
    capabilities: Dict[str, Any]
    serverInfo: Dict[str, Any]


class BaseConnector(ABC):
    """Base connector for MCP implementations"""

    def __init__(self):
        """Initialize base connector with common attributes"""
        self.session: Optional[ClientSession] = None
        self._tools: List[Tool] = []
        self._connected = False

    @property
    def tools(self) -> List[Tool]:
        """Get the list of available tools

        Returns:
            List of tools

        Raises:
            RuntimeError: If not initialized
        """
        if not self._connected:
            raise RuntimeError("Connector is not connected")
        return self._tools

    @abstractmethod
    async def connect(self) -> ClientSession:
        """Connect to MCP implementation

        Returns:
            Initialized MCP client session
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from MCP implementation"""
        pass

    async def initialize(self) -> Union[InitializeResult, Dict[str, Any]]:
        """Initialize the MCP session

        Returns:
            Session information

        Raises:
            RuntimeError: If not connected
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP implementation")

        # Initialize the session
        result = await self.session.initialize()

        # Get available tools
        tools_result = await self.session.list_tools()
        self._tools = tools_result.tools

        return result

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If not connected
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP implementation")

        return await self.session.call_tool(name, arguments)
