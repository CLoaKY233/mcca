# mcpclient/tools/extraction.py
import re
import json

# mcpclient/tools/extraction.py
from typing import List, Tuple, Dict, Any, Optional


class ToolExtractor:
    """Extracts tool calls from text"""

    @staticmethod
    def extract_tool_calls(
        text: str, available_tools: Optional[List[Any]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract tool calls from text

        Args:
            text: Text to extract tool calls from
            available_tools: List of available tools for fallback matching

        Returns:
            List of tuples containing (tool_name, parameters)
        """
        tool_calls = []

        # Look for the pattern TOOL: name followed by PARAMETERS: {...}
        tool_pattern = re.compile(
            r"TOOL:\s*([\w\-]+)\s*[\n\r]+\s*PARAMETERS:\s*({.*?})", re.DOTALL
        )

        matches = tool_pattern.findall(text)

        for tool_name, params_str in matches:
            try:
                # Try to parse the parameters as JSON
                # Remove any surrounding markdown backticks
                cleaned_params = params_str.strip("`").strip()
                params = json.loads(cleaned_params)
                tool_calls.append((tool_name.strip(), params))
            except json.JSONDecodeError:
                # If JSON parsing fails, add with empty params
                tool_calls.append((tool_name.strip(), {}))

        # Also look for a simpler pattern in case the model doesn't format correctly
        if not tool_calls and available_tools:
            for tool in available_tools:
                tool_mention = f"use the {tool.name} tool"
                if tool_mention.lower() in text.lower():
                    tool_calls.append((tool.name, {}))

        return tool_calls
