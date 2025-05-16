# MCP Client: A Comprehensive Guide to Model Context Protocol

The MCP Client in this repository demonstrates how to build AI applications that leverage the Model Context Protocol (MCP) for seamless integration between language models and external tools.

## Introduction to Model Context Protocol (MCP)

### What is MCP?

The Model Context Protocol (MCP) is an open standard introduced by Anthropic that standardizes how AI applications (chatbots, IDE assistants, or custom agents) connect with external tools, data sources, and systems.

Think of MCP like USB for AI integrations. Before USB, connecting peripherals required different ports and custom drivers. Similarly, integrating AI applications with external tools creates an "M×N problem" - with M different AI apps and N different tools, you potentially need M×N different integrations.

MCP transforms this into an "M+N problem" by providing a common protocol:
- Tool creators build N MCP servers (one for each system)
- Application developers build M MCP clients (one for each AI application)

### Core Architecture

MCP defines a client-server architecture with three primary components:

```mermaid
graph TD
    User[User] -->|Interacts with| Host[Host Application]
    Host -->|Sends requests to| Client[MCP Client]
    Client -->|Communicates via protocol| Server[MCP Server]
    Server -->|Provides| Tools[Tools]
    Server -->|Provides| Resources[Resources]
    Server -->|Provides| Prompts[Prompts]
    Host -->|Sends queries to| LLM[Language Model API]
    LLM -->|Requests tool execution| Client
```

1. **Hosts**: Applications the user interacts with (e.g., Claude Desktop, an IDE like Cursor)
2. **Clients**: Components within the Host that manage connections to MCP servers
3. **Servers**: External programs that expose capabilities through a standardized API

MCP servers provide three main capabilities:
- **Tools**: Functions that LLMs can call (similar to function calling)
- **Resources**: Data sources that LLMs can access (similar to GET endpoints)
- **Prompts**: Pre-defined templates for using tools or resources

## Project Architecture

This MCP client implementation uses a layered architecture:

```mermaid
graph TD
    API[API Layer: FastAPI] -->|Uses| Client[Client Core: MCPClient]
    Client -->|Connects via| Transport[Transport Layer: stdio_client]
    Client -->|Calls| LLM[LLM API: Anthropic Claude]
    Transport -->|Communicates with| Server[MCP Server]
```

### Key Components

1. **MCPClient**: The core client implementation (`mcp_client.py`)
2. **FastAPI Server**: HTTP API layer for interacting with the client (`main.py`)
3. **Logging**: Structured logging system (`utils/logger.py`)

## Installation

### Prerequisites

- Python 3.9+
- An Anthropic API key (for LLM interactions)
- Access to an MCP server (Python script or remote service)

### Setup Steps

```bash
# Clone the repository
git clone
cd mcpclient

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

## Core Client Implementation

The heart of the implementation is the `MCPClient` class in `mcp_client.py`:

```python
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = Anthropic()
        self.tools = []
        self.messages = []
        self.logger = logger
```

### Key Methods

#### Connecting to a Server

```python
async def connect_to_server(self, server_script_path: str):
    """Connect to an MCP server"""
    try:
        # Determine if script is Python or JavaScript
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")

        # Set up server parameters
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        # Create stdio transport
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport

        # Initialize MCP session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # Initialize the connection and retrieve tools
        await self.session.initialize()
        mcp_tools = await self.get_mcp_tools()

        # Format and store tools
        self.tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in mcp_tools
        ]
        return True
    except Exception as e:
        self.logger.error(f"Failed to connect to server: {str(e)}")
        raise Exception(f"Failed to connect to server: {str(e)}")
```

This method:
1. Determines the appropriate command to run the server script
2. Establishes a stdio connection to the server
3. Initializes an MCP session
4. Retrieves and formats available tools from the server

#### Processing Queries

The query processing workflow is where the magic happens:

```python
async def process_query(self, query: str):
    """Process a query using Claude and available tools"""
    try:
        # Add the initial user message
        user_message = {"role": "user", "content": query}
        self.messages.append(user_message)
        messages = [user_message]

        while True:
            # Call the language model
            response = await self.call_llm()

            # Handle simple text response
            if response.content[0].type == "text" and len(response.content) == 1:
                assistant_message = {
                    "role": "assistant",
                    "content": response.content[0].text,
                }
                self.messages.append(assistant_message)
                messages.append(assistant_message)
                break

            # Handle complex responses with tool calls
            assistant_message = {
                "role": "assistant",
                "content": response.to_dict()["content"],
            }
            self.messages.append(assistant_message)
            messages.append(assistant_message)

            # Process each content item
            for content in response.content:
                if content.type == "text":
                    # Text content
                    text_message = {"role": "assistant", "content": content.text}
                    messages.append(text_message)
                elif content.type == "tool_use":
                    # Tool call
                    tool_name = content.name
                    tool_args = content.input
                    tool_use_id = content.id

                    # Execute the tool
                    result = await self.session.call_tool(tool_name, tool_args)

                    # Create tool result message
                    tool_result_message = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result.content,
                            }
                        ],
                    }
                    self.messages.append(tool_result_message)
                    messages.append(tool_result_message)

        return messages
    except Exception as e:
        self.logger.error(f"Error processing query: {str(e)}")
        raise
```

This method:
1. Adds the user query to the conversation history
2. Calls the LLM with the current conversation and available tools
3. Processes the LLM response, which may include tool calls
4. For tool calls, executes the tool and adds the result to the conversation
5. Continues this loop until the LLM provides a final response
6. Returns the complete conversation history

## Workflow Diagrams

### Connection Flow

```mermaid
sequenceDiagram
    participant Client as MCPClient
    participant Server as MCP Server

    Client->>Server: Initialize connection
    Server-->>Client: Connection established
    Client->>Server: Request available tools
    Server-->>Client: Tool list with schemas
    Client->>Client: Store available tools
```

### Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant API as API Server
    participant Client as MCPClient
    participant LLM as Anthropic API
    participant Server as MCP Server

    User->>API: Send query
    API->>Client: Forward query
    Client->>LLM: Send query + available tools
    LLM-->>Client: Response (may include tool calls)

    alt Response contains tool calls
        Client->>Server: Execute tool call
        Server-->>Client: Tool result
        Client->>LLM: Send tool result
        LLM-->>Client: Updated response
    end

    Client-->>API: Final response
    API-->>User: Display response
```

### Tool Execution Flow

```mermaid
sequenceDiagram
    participant Client as MCPClient
    participant Server as MCP Server

    Client->>Server: call_tool(name, arguments)
    Server->>Server: Execute tool function
    Server-->>Client: Tool execution result
    Client->>Client: Format result for LLM
```

## API Server

The project includes a FastAPI server that exposes HTTP endpoints for interacting with the MCP client:

```python
@app.get("/tools")
async def get_available_tools():
    """Get list of available tools"""
    try:
        tools = await app.state.client.get_mcp_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def process_query(request: QueryRequest):
    """Process a query and return the response"""
    try:
        messages = await app.state.client.process_query(request.query)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool")
async def call_tool(tool_call: ToolCall):
    """Call a specific tool"""
    try:
        result = await app.state.client.call_tool(tool_call.name, tool_call.args)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Building Your Own MCP Server

To create an MCP server that your client can connect to, use the `fastmcp` library:

```python
from fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Calculator Server")

# Add a tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# Add a resource
@mcp.resource("weather://{city}")
def get_weather(city: str) -> dict:
    """Get weather for a city"""
    # Implementation here
    return {"city": city, "condition": "sunny", "temperature": 72}

# Run the server
if __name__ == "__main__":
    mcp.run()
```

## Transport Types

MCP supports multiple transport protocols:

1. **STDIO (Default)**: Best for local tools and command-line scripts
   ```python
   mcp.run(transport="stdio")  # Default
   ```

2. **Streamable HTTP**: Recommended for web deployments
   ```python
   mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, path="/mcp")
   ```

3. **Server-Sent Events (SSE)**: For compatibility with existing SSE clients
   ```python
   mcp.run(transport="sse", host="127.0.0.1", port=8000)
   ```

## Running the Client

### Command Line Interface

```bash
# Run the script.py client connected to an MCP server
python script.py path/to/server_script.py
```

### API Server

```bash
# Start the API server
cd api
uvicorn main:app --reload
```

## Advanced Usage

### Custom Tool Development

To extend functionality, create custom tools in your MCP server:

```python
@mcp.tool()
def search_database(query: str, max_results: int = 10) -> List[Dict]:
    """Search database for matching records"""
    # Implementation here
    results = [{"id": 1, "title": "Example result", "score": 0.95}]
    return results[:max_results]
```

### Error Handling Strategy

The client implements comprehensive error handling:

1. **Connection Errors**: When server connection fails
2. **Tool Execution Errors**: When tools throw exceptions
3. **LLM API Errors**: When the model service is unavailable

All errors are logged and propagated appropriately to the caller.

## Troubleshooting

### Common Issues

1. **Connection Failures**:
   - Ensure the server script path is correct
   - Check that the script is executable
   - Verify the script implements the MCP server protocol

2. **Tool Execution Errors**:
   - Check that tool arguments match the expected schema
   - Verify the tool implementation on the server
   - Review server logs for error details

3. **LLM API Errors**:
   - Verify your Anthropic API key is valid
   - Ensure you have sufficient API credits
   - Check if the model service is available

### Debugging Tips

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Conclusion

This MCP client implementation provides a robust foundation for building AI applications that can interact with external tools and services through the Model Context Protocol. By following this guide, you can understand how MCP works, how this client is structured, and how to build your own MCP-enabled applications.

The separation of concerns between clients, servers, and the protocol itself creates a flexible ecosystem where AI models can seamlessly access external functionality without requiring custom integrations for each model-tool combination.

For the latest updates and more information about MCP, visit the [Model Context Protocol website](https://modelcontextprotocol.io/).

Citations:
[1] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/39469378/2e4f8f08-6440-4f6e-ad20-1efbbcf89670/paste.txt
[2] https://arxiv.org/abs/2402.07463
[3] https://docs.llamaindex.ai/en/latest/api_reference/tools/mcp/
[4] https://modelcontextprotocol.io/docs/concepts/architecture
[5] https://huggingface.co/learn/mcp-course/unit1/architectural-components
[6] https://pypi.org/project/mcp/
[7] https://www.philschmid.de/mcp-introduction
[8] https://modelcontextprotocol.io/quickstart/client
[9] https://arxiv.org/abs/2406.16650
[10] https://pypi.org/project/fastmcp/
[11] https://www.semanticscholar.org/paper/3a9dde1f74629a865e8db041e15400e17a47ce9e
[12] https://www.semanticscholar.org/paper/b42f10b12f403d729ccdd0676a19781c58e90206
[13] https://www.semanticscholar.org/paper/d72f328592b1fcb44dfcfa24345f431ddc8791f1
[14] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10990682/
[15] https://arxiv.org/abs/2403.07884
[16] https://arxiv.org/abs/2310.14776
[17] https://www.semanticscholar.org/paper/43a75a247c788e10ede621169120832b3e124d4f
[18] https://arxiv.org/abs/2301.02057
[19] http://arxiv.org/pdf/2010.00724.pdf
[20] https://arxiv.org/pdf/2501.00539.pdf
[21] https://www.semanticscholar.org/paper/6370811ea9ac62edaccbf7b747754b20e6f68c57
[22] https://www.semanticscholar.org/paper/72a860651eb23aa4f4328d06aa323fe2eb1e3e1a
[23] https://www.semanticscholar.org/paper/e25c9476deab58bb6643394e2d298add9ed823f3
[24] https://www.semanticscholar.org/paper/1efb32afdd2c6173dff2d2157f6226d08d12dba2
[25] https://arxiv.org/html/2411.03945v1
[26] https://arxiv.org/html/2407.05566v1
[27] https://arxiv.org/html/2306.08659v2
[28] http://arxiv.org/pdf/1007.5092.pdf
[29] https://portkey.ai/blog/model-context-protocol-for-llm-appls
[30] https://www.searchunify.com/short-articles/the-technical-backbone-of-mcp-architecture-how-it-works/
[31] https://learn.microsoft.com/en-us/azure/api-center/register-discover-mcp-server
[32] https://www.semanticscholar.org/paper/7319c2bd0824849e8793d8066b49ff4ae6a56826
[33] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8135227/
[34] https://www.semanticscholar.org/paper/edde3a528eeac8025ce5e430148d78caf142581a
[35] https://www.semanticscholar.org/paper/58be2bff5ca9c540b5ec929998d3c0880bd49021
[36] https://arxiv.org/pdf/2402.12203.pdf
[37] http://arxiv.org/pdf/1609.00381.pdf
[38] https://arxiv.org/pdf/2111.04872.pdf
[39] https://arxiv.org/pdf/1907.11073.pdf
[40] https://github.com/dexaai/mcp-quickstart
[41] https://pypi.org/project/mcp-server-docs/
[42] https://www.youtube.com/watch?v=5xqFjh56AwM
[43] https://googleapis.github.io/genai-toolbox/getting-started/mcp_quickstart/
[44] https://pubmed.ncbi.nlm.nih.gov/39714765/
[45] https://www.semanticscholar.org/paper/f8fc91cd3adaf53ecb1b671a2b300aaeb4b0ba7c
[46] https://www.semanticscholar.org/paper/9b14009e11506cf38c6b2397ebd5c03b6bcf62d9
[47] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10492165/
[48] https://arxiv.org/pdf/2203.08774.pdf
[49] https://en.wikipedia.org/wiki/Model_Context_Protocol
[50] https://openai.github.io/openai-agents-python/mcp/
[51] http://arxiv.org/pdf/2208.14908.pdf
[52] https://arxiv.org/abs/1510.06638
[53] https://arxiv.org/pdf/1712.00263.pdf
[54] http://arxiv.org/pdf/2010.15444v1.pdf
[55] https://github.com/adhikasp/mcp-client-cli
[56] https://www.youtube.com/watch?v=Ek8JHgZtmcI
[57] https://aiengineering.academy/Agents/MCP/CreateMCPServe/
[58] https://neon.tech/blog/building-a-cli-client-for-model-context-protocol-servers
[59] https://github.com/lastmile-ai/mcp-agent/issues/115
[60] https://www.semanticscholar.org/paper/079b7a11c8328c2f42682fc565d97245ed127a15
[61] https://www.semanticscholar.org/paper/bb24e2600911f983f9d28fd0d822d69ad5e623c6
[62] https://arxiv.org/abs/2505.07838
[63] https://www.linkedin.com/pulse/securing-model-context-protocol-mcp-architecture-best-srivastava-v4hgf
[64] https://github.com/peng-shawn/mermaid-mcp-server
[65] https://www.linkedin.com/pulse/simple-guide-model-context-protocol-mcp-yugank-aman-tjbsf
[66] https://www.youtube.com/watch?v=Ui44L09in2s
[67] https://arxiv.org/pdf/2009.00326.pdf
[68] https://arxiv.org/pdf/2104.03822.pdf
[69] http://arxiv.org/pdf/2107.12550.pdf
[70] http://arxiv.org/pdf/1811.00542.pdf
[71] https://arxiv.org/pdf/2501.15897.pdf
[72] https://arxiv.org/abs/1911.12661
[73] http://arxiv.org/pdf/2409.04668.pdf
[74] https://ai.pydantic.dev/mcp/run-python/
[75] https://github.com/jlowin/fastmcp
[76] https://github.com/ruslanmv/Simple-MCP-Server-with-Python
[77] https://modelcontextprotocol.io/sdk/java/mcp-client
[78] https://mirascope.com/learn/mcp/client/
[79] https://hiddenlayer.com/innovation-hub/exploiting-mcp-tool-parameters/
[80] https://pypi.org/project/mcp-agent/
[81] https://arxiv.org/abs/2504.21030
[82] https://arxiv.org/abs/2504.08623
[83] https://www.semanticscholar.org/paper/b71a4cce413869a54e0007a820ed7d185947bfd6
[84] https://www.semanticscholar.org/paper/ba3e7af17e1890d23ecff7b26daffc619c910336
[85] https://www.semanticscholar.org/paper/f753519cb38d4c193ef3abcdea7cbc1db41a152f
[86] https://www.semanticscholar.org/paper/6c3b4c0c1803d50c0dc678b4af6e50fbb8f86360
[87] https://arxiv.org/pdf/2503.23278.pdf
[88] https://arxiv.org/html/2310.08049
[89] https://arxiv.org/pdf/0812.3716.pdf
[90] https://arxiv.org/html/2502.20320v1
[91] https://arxiv.org/html/2504.03767v2
[92] https://www.datacamp.com/tutorial/mcp-model-context-protocol
[93] https://www.anthropic.com/news/model-context-protocol
[94] https://opencv.org/blog/model-context-protocol/
[95] https://composio.dev/blog/what-is-model-context-protocol-mcp-explained/
[96] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12007596/
[97] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10794684/
[98] https://arxiv.org/abs/2309.11021
[99] https://arxiv.org/abs/2309.02637
[100] https://arxiv.org/abs/2308.05942
[101] https://arxiv.org/abs/2306.16307
[102] http://arxiv.org/pdf/2305.10612.pdf
[103] http://arxiv.org/pdf/2209.13643.pdf
[104] https://pypi.org/project/mcp-atlassian/
[105] https://libraries.io/pypi/mcp-python
[106] https://www.youtube.com/watch?v=oq3dkNm51qc
[107] https://arxiv.org/abs/2503.23278
[108] https://www.semanticscholar.org/paper/0b9fb62a1570e344d1dff53607d26eebe7a31b95
[109] https://www.semanticscholar.org/paper/355bd38ab187200a4c21d46d8694be38fc97a41a
[110] https://arxiv.org/abs/2409.02434
[111] https://www.semanticscholar.org/paper/9949bd28cecd0709357aaf736059da1d5b6d30db
[112] https://www.semanticscholar.org/paper/46005ee74bbff80250ac4f8960bbc90aa336eaf5
[113] https://arxiv.org/pdf/2003.05055.pdf
[114] https://arxiv.org/pdf/1503.07159.pdf
[115] https://arxiv.org/pdf/1606.05939.pdf
[116] https://modelcontextprotocol.io/introduction
[117] https://modelcontextprotocol.io/specification/2025-03-26
[118] https://arxiv.org/pdf/1106.0868.pdf
[119] https://github.com/modelcontextprotocol/python-sdk
[120] https://modelcontextprotocol.io/quickstart/server
[121] https://github.com/modelcontextprotocol/quickstart-resources
[122] https://www.youtube.com/watch?v=jLM6n4mdRuA
[123] https://arxiv.org/abs/2505.01834
[124] https://www.semanticscholar.org/paper/d94110f998188446acd6c0217bccf5ecc46cb12a
[125] https://www.semanticscholar.org/paper/6bcb1496f53c54ea51a0de777e010b5387818d63
[126] https://mermaid.js.org/syntax/architecture.html
[127] https://www.descope.com/learn/post/mcp
[128] https://mermaid.js.org/syntax/sequenceDiagram.html
[129] https://devblogs.microsoft.com/dotnet/build-a-model-context-protocol-mcp-server-in-csharp/
[130] https://github.com/rtuin/mcp-mermaid-validator
[131] https://playbooks.com/mcp/longjianjiang-mermaid
[132] https://www.pulsemcp.com/servers/reblabers-mermaid-diagram-generator

---
Answer from Perplexity: pplx.ai/share