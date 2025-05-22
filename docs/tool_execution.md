# Tool Execution

This document explains how the MCP Client handles tool extraction and execution when working with language models.

## Overview

The MCP Client uses a two-step process for tool handling:

1. **Tool Extraction**: Identifying tool calls in the LLM's response
2. **Tool Execution**: Sending tool calls to the MCP server and handling results

These processes are implemented in the `ToolExtractor` and `ToolExecutor` classes respectively.

## Tool Extraction

### Pattern Recognition

The `ToolExtractor` class is responsible for parsing LLM responses to find tool calls. It looks for a specific pattern:

```
TOOL: tool_name
PARAMETERS: {"param1": "value1", "param2": "value2"}
```

The implementation is in `mcpclient/tools/extraction.py`:

```python
def extract_tool_calls(text: str, available_tools: Optional[List[Any]] = None) -> List[Tuple[str, Dict[str, Any]]]:
    """Extract tool calls from text"""
    tool_calls = []

    # Look for the pattern TOOL: name followed by PARAMETERS: {...}
    tool_pattern = re.compile(
        r"TOOL:\s*([\w\-]+)\s*[\n\r]+\s*PARAMETERS:\s*({.*?})", re.DOTALL
    )

    matches = tool_pattern.findall(text)
    
    # Process matches...
    
    return tool_calls
```

### Fallback Matching

If the standard pattern isn't found but tools are mentioned, the extractor uses a fallback mechanism to try and identify tool calls based on tool names:

```python
# Also look for a simpler pattern in case the model doesn't format correctly
if not tool_calls and available_tools:
    for tool in available_tools:
        tool_mention = f"use the {tool.name} tool"
        if tool_mention.lower() in text.lower():
            tool_calls.append((tool.name, {}))
```

## Tool Execution

### Validation

Before executing a tool, the `ToolExecutor` validates arguments against the tool's schema:

```python
def validate_tool_args(tool, args: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Validate tool arguments against schema"""
    # Implementation checks required fields and property types
```

The validation process checks:
- Required fields are present
- Parameter types match expected types
- Attempts type conversions where possible

### Execution

Tool execution is handled by sending the validated parameters to the MCP server:

```python
async def execute_tool(session, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, Any, str]:
    """Execute a tool and process the result"""
    try:
        # Execute tool
        result = await session.call_tool(tool_name, tool_args)

        # Format the result for display
        formatted_result = ToolExecutor.format_tool_result(result)

        return True, result, formatted_result
    except Exception as e:
        # Handle errors
```

### Result Formatting

Tool results are formatted for display and further processing:

```python
def format_tool_result(result) -> str:
    """Format tool result for display"""
    # Handle different result types and formats
```

The formatting handles various result types including:
- String content
- List content
- Structured data
- Error messages

## Multi-Turn Tool Execution Flow

The client supports multi-turn tool execution with the following flow:

1. User sends a query
2. LLM generates a response
3. Tool calls are extracted from the response
4. Tools are executed on the MCP server
5. Tool results are sent back to the LLM
6. LLM generates a follow-up response
7. Steps 3-6 repeat until no more tool calls or maximum turns reached

This process allows for complex, multi-step interactions that may require multiple tool calls.

## Error Handling

Tool execution includes comprehensive error handling:

1. **Extraction Errors**: When the LLM's tool call format is incorrect
2. **Validation Errors**: When tool arguments don't match the schema
3. **Execution Errors**: When the tool fails on the server
4. **Result Formatting Errors**: When the result can't be properly formatted

All errors are captured, formatted, and provided back to the LLM to allow it to recover or suggest alternatives.

## Streaming Integration

Tool execution is integrated with the streaming response system:

1. When a tool call is detected, execution status is streamed to the user
2. Tool execution progress and results are shown in real-time
3. The LLM's follow-up response after seeing tool results is also streamed

This creates a seamless experience where users can see exactly what's happening during complex interactions.