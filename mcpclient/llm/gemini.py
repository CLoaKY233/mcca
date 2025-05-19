# mcpclient/llm/gemini.py
# type: ignore
import os
from typing import List, Dict, Any, AsyncGenerator, Optional
import google.generativeai as genai

from .base import BaseLLM
from dotenv import load_dotenv

load_dotenv()


class GeminiLLM(BaseLLM):
    """Gemini LLM integration"""

    def __init__(
        self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash"
    ):
        """Initialize Gemini LLM

        Args:
            api_key: Gemini API key
            model_name: Model name
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not provided and not found in environment variables"
            )

        self.model_name = model_name
        genai.configure(api_key=self.api_key)

    def _create_model(self):
        """Create Gemini model instance"""
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={"max_output_tokens": 1000, "temperature": 0.2},
        )

    def _prepare_messages(
        self, messages: List[Dict[str, Any]], tool_info: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prepare messages for Gemini

        Args:
            messages: Input messages
            tool_info: Information about available tools

        Returns:
            Properly formatted messages for Gemini
        """
        gemini_messages = []

        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]

            # Add tool info to the first user message
            if role == "user" and len(gemini_messages) == 0 and tool_info:
                content += tool_info

            gemini_messages.append({"role": role, "parts": [{"text": content}]})

        return gemini_messages

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
        model = self._create_model()
        gemini_messages = self._prepare_messages(messages, tool_info)

        response = model.generate_content(gemini_messages)
        return response.text if hasattr(response, "text") else ""

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
        model = self._create_model()
        gemini_messages = self._prepare_messages(messages, tool_info)

        response = model.generate_content(gemini_messages, stream=True)

        for chunk in response:
            if hasattr(chunk, "text"):
                yield chunk.text
