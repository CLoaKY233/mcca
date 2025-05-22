# MCP Client Documentation

## Overview

MCP Client is a Python library that implements the Model Context Protocol (MCP), allowing AI applications to connect seamlessly with external tools and services. This documentation covers installation, usage, and technical details of the implementation.

## Contents

1. [Installation Guide](installation.md) - How to set up the MCP Client
2. [LLM Integration](llm_integration.md) - Working with different language models
3. [Streaming Implementation](streaming.md) - Details on the real-time streaming functionality
4. [Tool Execution](tool_execution.md) - How tools are extracted and executed

## Key Features

- **Multiple LLM Support**: Integrates with both GitHub's GPT models and Google Gemini
- **Efficient Streaming**: Real-time response streaming with non-blocking UI updates
- **Multi-Turn Tool Execution**: Support for complex interactions requiring multiple tool calls
- **Flexible Architecture**: Modular design for easy extension and customization

## Quick Start

```python
from mcpclient.client import MCPClient

# Initialize client with config file
client = MCPClient(config_path="config.json")

# Connect to a server
await client.connect_to_server("MyServer")

# Process a query with streaming response
async for chunk in client.process_query_streaming("Calculate 25 * 16"):
    print(chunk, end="", flush=True)

# Cleanup when done
await client.disconnect()
```

## Web Interface

The web interface provides a user-friendly way to interact with MCP servers:

```bash
# Start the web interface
streamlit run app.py
```

## Command Line Interface

The CLI offers a simple way to test and use the client:

```bash
# Start CLI with config file
python cli.py config.json
```

## Architecture

The MCP Client uses a layered architecture:

- **Client Layer**: Main interface for applications
- **Session Layer**: Manages MCP session lifecycle
- **Connector Layer**: Handles communication with MCP servers
- **LLM Layer**: Integrates with language models
- **Tool Layer**: Extracts and executes tools

## License

This project is available under the MIT License. See the LICENSE file for details.