# LLM Integration

The MCP Client supports multiple LLM providers through a flexible integration architecture. This document explains how the client integrates with different language models and how to configure them.

## Available LLM Integrations

### 1. GitHub's GPT-4.1 (Default)

The client uses GitHub's hosted GPT-4.1 model by default. This is a high-quality OpenAI-based model that offers excellent tool use capabilities.

#### Configuration

```python
from mcpclient.llm.gpt4o import GptLLM

# Initialize with your GitHub token
llm = GptLLM(api_key="your_github_token")

# Or use the token from environment variables
llm = GptLLM()  # Reads from GITHUB_TOKEN env var
```

#### Environment Setup

```
GITHUB_TOKEN=your_github_token_here
```

### 2. Google Gemini

An alternative integration with Google's Gemini models.

#### Configuration

```python
from mcpclient.llm.gemini import GeminiLLM

# Initialize with your Gemini API key
llm = GeminiLLM(api_key="your_gemini_key")

# Or use the key from environment variables
llm = GeminiLLM()  # Reads from GEMINI_API_KEY env var
```

#### Environment Setup

```
GEMINI_API_KEY=your_gemini_api_key_here
```

## Using Custom LLMs

You can implement your own LLM integration by extending the `BaseLLM` class:

```python
from mcpclient.llm.base import BaseLLM

class MyCustomLLM(BaseLLM):
    def __init__(self, api_key=None, model_name=None):
        self.api_key = api_key
        self.model_name = model_name
        
    async def generate(self, messages, tool_info=None):
        # Your implementation here
        pass
        
    async def generate_streaming(self, messages, tool_info=None):
        # Your streaming implementation here
        yield "Your generated text chunks"
```

Then use your custom LLM with the client:

```python
custom_llm = MyCustomLLM(api_key="your_key", model_name="your_model")
client = MCPClient(config_path="config.json")
client.llm = custom_llm
```

## Implementation Details

### Message Formatting

Each LLM implementation handles message formatting differently:

- **GitHub/OpenAI**: Uses the standard chat completion format with role-based messages
- **Gemini**: Converts messages to Gemini's specific format with parts

### Tool Information

Tool information is passed to the LLM as formatted text added to the first user message. For example:

```
User query

Available tools:
- get_weather: Get weather information for a location
  Parameters:
    - location (required): The city or location to get weather for
    - units: The units to use (metric or imperial)
...

To call a tool, use this format in your response:
TOOL: tool_name
PARAMETERS: {"param1": "value1", "param2": "value2"}
```

### Streaming Implementation

The streaming implementation uses async generators to yield text chunks as they become available, allowing for a responsive user experience:

- **GitHub/OpenAI**: Uses OpenAI's native streaming support with async chunks
- **Gemini**: Uses Gemini's streaming API and transforms it into async yielded chunks

## Error Handling

Each LLM implementation includes error handling for common issues:

1. Authentication errors (invalid API keys)
2. Rate limiting and quota issues
3. Network connectivity problems
4. Model-specific errors

Errors are caught and either raised with contextual information or yielded as error messages in the streaming response.

## Best Practices

1. **Environment Variables**: Always store API keys in environment variables
2. **Error Handling**: Add appropriate try/except blocks when calling LLM methods
3. **Streaming**: Prefer streaming for better user experience with long responses
4. **Model Selection**: Choose the appropriate model for your task based on capabilities and cost