# mcpclient/llm/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional


class BaseLLM(ABC):
    """Base class for LLM integration"""

    @abstractmethod
    async def generate(
        self, messages: List[Dict[str, Any]], tool_info: Optional[str] = None
    ) -> str:
        """Generate a response

        Args:
            messages: Messages for context
            tool_info: Information about available tools

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def generate_streaming(
        self, messages: List[Dict[str, Any]], tool_info: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a response with streaming

        Args:
            messages: Messages for context
            tool_info: Information about available tools

        Yields:
            Generated text chunks
        """
        pass
