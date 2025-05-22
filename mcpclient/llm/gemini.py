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

        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg["content"]

            # Convert tool results to a formatted text representation
            if role == "tool":
                # Tool results need to be formatted as text since Gemini Python SDK
                # doesn't directly support functionResponse in parts
                if isinstance(content, dict):
                    tool_name = content.get("tool_name", "unknown_tool")
                    tool_result = content.get("result")
                    tool_error = content.get("error")

                    # Format as clearly marked text that the LLM can understand
                    formatted_text = f"### TOOL RESULT: {tool_name}\n"
                    if tool_result is not None:
                        formatted_text += f"{tool_result}\n"
                    elif tool_error is not None:
                        formatted_text += f"ERROR: {tool_error}\n"

                    # Add as a user message since Gemini understands user/model roles
                    gemini_messages.append(
                        {"role": "user", "parts": [{"text": formatted_text}]}
                    )
                else:
                    # Fallback for unexpected format
                    gemini_messages.append(
                        {
                            "role": "user",
                            "parts": [{"text": f"Tool result: {str(content)}"}],
                        }
                    )

            elif role == "user":
                user_content = content
                # Add tool info to the first user message only
                if i == 0 and tool_info:
                    user_content += tool_info

                gemini_messages.append(
                    {"role": "user", "parts": [{"text": user_content}]}
                )

            elif role == "model":
                if content:  # Skip empty model responses
                    gemini_messages.append(
                        {"role": "model", "parts": [{"text": content}]}
                    )

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
