import json
from typing import Dict, Any, List, Tuple, Optional
import traceback


class ToolExecutor:
    """Executes MCP tools and processes results"""

    @staticmethod
    async def execute_tool(
        session, tool_name: str, tool_args: Dict[str, Any]
    ) -> Tuple[bool, Any, str]:
        """Execute a tool and process the result

        Args:
            session: The MCP session
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tuple of (success, result, formatted_result)
        """
        try:
            # Execute tool
            result = await session.call_tool(tool_name, tool_args)

            # Format the result for display
            formatted_result = ToolExecutor.format_tool_result(result)

            return True, result, formatted_result

        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            traceback.print_exc()
            return False, None, error_msg

    @staticmethod
    def format_tool_result(result) -> str:
        """Format tool result for display

        Args:
            result: The raw tool result

        Returns:
            Formatted result string
        """
        # Handle different result types
        if hasattr(result, "content"):
            content = result.content

            # Handle string content
            if isinstance(content, str):
                return content

            # Handle list of content items
            if isinstance(content, list):
                formatted_parts = []
                for item in content:
                    if hasattr(item, "text"):
                        formatted_parts.append(item.text)
                    elif hasattr(item, "data"):
                        formatted_parts.append(f"[Image/Data: {item.data[:20]}...]")
                    else:
                        formatted_parts.append(str(item))
                return "\n".join(formatted_parts)

            # Handle other content types
            return str(content).replace("\\n", "\n")

        # Default fallback
        return str(result)

    @staticmethod
    def validate_tool_args(
        tool, args: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate tool arguments against schema

        Args:
            tool: The tool object with schema
            args: The arguments to validate

        Returns:
            Tuple of (is_valid, processed_args, error_message)
        """
        if not hasattr(tool, "inputSchema") or not tool.inputSchema:
            # No schema to validate against
            return True, args, None

        schema = tool.inputSchema
        processed_args = args.copy()

        # Check required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in args:
                    return False, None, f"Missing required field: {field}"

        # Check property types (basic validation)
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                if prop_name in args:
                    prop_type = prop_schema.get("type")

                    # Skip validation if type is not specified
                    if not prop_type:
                        continue

                    value = args[prop_name]

                    # Handle null values
                    if value is None:
                        if prop_type == "null" or (
                            isinstance(prop_type, list) and "null" in prop_type
                        ):
                            continue
                        else:
                            return False, None, f"Field {prop_name} cannot be null"

                    # Handle simple types
                    if prop_type == "string" and not isinstance(value, str):
                        # Try to convert to string
                        processed_args[prop_name] = str(value)
                    elif prop_type == "number" and not isinstance(value, (int, float)):
                        try:
                            processed_args[prop_name] = float(value)
                        except (ValueError, TypeError):
                            return False, None, f"Field {prop_name} must be a number"
                    elif prop_type == "integer" and not isinstance(value, int):
                        try:
                            processed_args[prop_name] = int(value)
                        except (ValueError, TypeError):
                            return False, None, f"Field {prop_name} must be an integer"
                    elif prop_type == "boolean" and not isinstance(value, bool):
                        # Handle string representations of booleans
                        if isinstance(value, str):
                            if value.lower() == "true":
                                processed_args[prop_name] = True
                            elif value.lower() == "false":
                                processed_args[prop_name] = False
                            else:
                                return (
                                    False,
                                    None,
                                    f"Field {prop_name} must be a boolean",
                                )
                        else:
                            return False, None, f"Field {prop_name} must be a boolean"
                    elif prop_type == "array" and not isinstance(value, list):
                        # Try to convert string to array if it looks like JSON
                        if isinstance(value, str) and value.strip().startswith("["):
                            try:
                                processed_args[prop_name] = json.loads(value)
                            except json.JSONDecodeError:
                                return (
                                    False,
                                    None,
                                    f"Field {prop_name} must be an array",
                                )
                        else:
                            return False, None, f"Field {prop_name} must be an array"
                    elif prop_type == "object" and not isinstance(value, dict):
                        # Try to convert string to object if it looks like JSON
                        if isinstance(value, str) and value.strip().startswith("{"):
                            try:
                                processed_args[prop_name] = json.loads(value)
                            except json.JSONDecodeError:
                                return (
                                    False,
                                    None,
                                    f"Field {prop_name} must be an object",
                                )
                        else:
                            return False, None, f"Field {prop_name} must be an object"

        return True, processed_args, None

    @staticmethod
    def find_tool_by_name(tools: List[Any], tool_name: str) -> Optional[Any]:
        """Find a tool by name

        Args:
            tools: List of tools
            tool_name: Name of the tool to find

        Returns:
            The tool object if found, None otherwise
        """
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None
