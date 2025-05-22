import os
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional, cast
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam

from .base import BaseLLM
from dotenv import load_dotenv

load_dotenv()
endpoint = "https://models.github.ai/inference"

class GptLLM(BaseLLM):
    """OpenAI LLM integration for GitHub's models"""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "openai/gpt-4.1"):
        """
        Initialize OpenAI LLM
        Args:
            api_key: GitHub API token
            model_name: Model name
        """

        self.api_key = api_key or os.environ.get("GITHUB_TOKEN")
        if not self.api_key:
            raise ValueError(
                "GITHUB_TOKEN not provided and not found in environment variables"
            )
        self.model_name = model_name

    def _create_sync_client(self):
        """Create synchronous OpenAI client for GitHub models"""
        return OpenAI(
            base_url=endpoint,
            api_key=self.api_key,
        )

    def _create_async_client(self):
        """Create asynchronous OpenAI client for GitHub models"""
        return AsyncOpenAI(
            base_url=endpoint,
            api_key=self.api_key,
        )

    def _prepare_messages(
        self, messages: List[Dict[str, Any]], tool_info: Optional[str] = None
    ) -> List[ChatCompletionMessageParam]:
        """Prepare messages for OpenAI

        Args:
            messages: Input messages
            tool_info: Information about available tools

        Returns:
            Properly formatted messages for OpenAI
        """
        openai_messages: List[ChatCompletionMessageParam] = []
        system_message: ChatCompletionSystemMessageParam = {"role": "system", "content": "You are a helpful assistant."}
        openai_messages.append(system_message)

        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                # Add tool info to the first user message if provided
                if i == 0 and tool_info:
                    content = f"{content}\n\n{tool_info}"
                user_message: ChatCompletionUserMessageParam = {"role": "user", "content": content}
                openai_messages.append(user_message)

            elif role == "model" or role == "assistant":
                # OpenAI uses "assistant" rather than "model"
                if content:  # Skip empty responses
                    assistant_message: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": content}
                    openai_messages.append(assistant_message)

            elif role == "tool":
                # Convert tool messages to user messages in the format client.py expects
                tool_content = "TOOL RESULT: "
                if isinstance(content, dict):
                    tool_name = content.get("tool_name", "unknown_tool")
                    tool_content += f"{tool_name}\n"

                    if "result" in content:
                        tool_content += str(content["result"])
                    elif "error" in content:
                        tool_content += f"ERROR: {content['error']}"
                else:
                    tool_content += str(content)

                tool_message: ChatCompletionUserMessageParam = {"role": "user", "content": tool_content}
                openai_messages.append(tool_message)

        return openai_messages

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
        openai_messages = self._prepare_messages(messages, tool_info)

        # Run the API call in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        client = self._create_sync_client()

        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                temperature=0.2,
                max_tokens=3000
            )
        )

        # Handle potential None case
        content = response.choices[0].message.content
        return content if content is not None else ""

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
        client = self._create_async_client()
        openai_messages = self._prepare_messages(messages, tool_info)

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                temperature=0.2,
                max_tokens=1000,
                stream=True
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            # Yield the error as a chunk to make it visible in the stream
            yield f"\n[Error in LLM streaming: {str(e)}]"
            # Re-raise to let caller handle it
            raise
