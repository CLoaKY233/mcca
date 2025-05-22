# Streaming Implementation

The MCP Client includes an advanced streaming implementation for real-time response display. This document explains how the streaming works in both the CLI and web interfaces.

## Overview

Streaming allows responses to be displayed incrementally as they are generated, rather than waiting for the complete response. This creates a more responsive user experience and allows for multi-turn tool execution to happen seamlessly.

## Key Components

### 1. Client-Level Streaming

The core streaming functionality is implemented in `MCPClient.process_query_streaming()`:

```python
async def process_query_streaming(self, query: str) -> AsyncGenerator[str, None]:
    """Process a query with streaming response.

    Simple flow:
    1. User sends message
    2. LLM responds
    3. If response has tool call, execute tool
    4. Send tool result back to LLM
    5. Repeat 2-4 until no more tool calls
    """
```

This method:
- Streams the initial LLM response
- Detects tool calls in the response
- Executes tools and yields tool execution status
- Feeds tool results back to the LLM
- Continues this cycle with a maximum turn limit to prevent infinite loops

### 2. Web Interface Streaming

The Streamlit web interface (`app.py`) implements a non-blocking approach for streaming responses:

1. **Background Processing**: Queries are processed in a separate thread to prevent blocking the UI
   ```python
   def process_query_thread(config_path, server_name, query, session_id):
       """Process a query in a background thread using a new client instance"""
   ```

2. **Status Monitoring**: The UI checks the status of the streaming response without requiring reruns
   ```python
   def check_streaming_status():
       """Check the status of streaming response"""
   ```

3. **File-Based Communication**: Uses temp files to communicate between the processing thread and the UI thread

## Advantages Over Previous Implementation

The current streaming implementation offers several advantages:

1. **Non-Blocking UI**: The web interface remains responsive during streaming
2. **Reduced Reruns**: Eliminated the need for Streamlit reruns, which improves performance
3. **Multi-Turn Tool Execution**: Supports complex interactions with multiple tool calls
4. **Graceful Error Handling**: Errors in tool execution are captured and streamed as part of the response
5. **Support for Long-Running Tools**: Tools that take longer to execute don't freeze the UI

## Implementation Details

### Temporary File Communication

The web interface uses temporary files to communicate between threads:

1. **Response File**: Contains the current accumulated response text
2. **Status File**: Contains JSON status information (completion status, current tool, errors)

```python
response_file = os.path.join(temp_dir, f"response_{session_id}.txt")
status_file = os.path.join(temp_dir, f"status_{session_id}.json")
```

### Tool Execution Visualization

When a tool is being executed, the streaming UI shows:
1. The tool being executed
2. The parameters passed to the tool
3. The result from the tool

Example output:
```
🔧 Using tool: calculate
📝 Parameters: {"expression": "5 * 12"}
📊 Result:
60
```

## CLI Streaming Implementation

The CLI implementation uses direct async streaming:

```python
async for chunk in client.process_query_streaming(query):
    print(chunk, end="", flush=True)
```

This provides real-time output directly to the terminal without any additional threading.

## LLM Streaming Support

Each LLM implementation provides its own streaming implementation:

1. **GitHub/OpenAI**: Uses native OpenAI streaming with `stream=True`
2. **Gemini**: Uses Gemini's streaming implementation

## Maximum Turn Limit

To prevent infinite loops in tool execution, a maximum turn limit is enforced:

```python
max_turns = 10
turn_count = 0

while turn_count < max_turns:
    # Process turns
```

This ensures the streaming process eventually completes even if the LLM keeps trying to use tools.

## Debugging Streaming Issues

When troubleshooting streaming issues:

1. Check if temporary files are being created and updated
2. Look for errors in the status file
3. Verify that the UI is checking the status properly
4. Ensure the background thread is properly initialized and running