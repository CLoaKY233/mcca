# Configuration Guide

## Overview

The MCP Client uses JSON configuration files to define server connections and settings. This document explains the configuration options and best practices for setting up your MCP client.

## Configuration File Format

The configuration file is a JSON document with the following structure:

```json
{
  "context_servers": {
    "ServerName1": {
      "command": {
        "path": "executable_path",
        "args": ["arg1", "arg2"],
        "env": {
          "ENV_VAR1": "value1",
          "ENV_VAR2": "value2"
        }
      },
      "settings": {
        "setting1": "value1",
        "setting2": "value2"
      }
    },
    "ServerName2": {
      // Another server configuration...
    }
  }
}
```

## Configuration Options

### Server Configuration

Each server in the `context_servers` object has the following properties:

#### `command` (Required)

Defines how to start the MCP server:

- `path` (Required): Path to the executable or interpreter
- `args` (Optional): Array of command-line arguments
- `env` (Optional): Environment variables to set when running the server. These variables will be added to or override the existing environment for the server process.

#### `settings` (Optional)

Server-specific settings that can be used by the client or passed to the server.

## Example Configurations

### Python Script Server

```json
{
  "context_servers": {
    "PythonServer": {
      "command": {
        "path": "python",
        "args": ["path/to/server.py"],
        "env": {
          "PYTHONPATH": "/path/to/your/project/root",
          "DEBUG": "true"
        }
      }
    }
  }
}
```
*Note: For `PYTHONPATH` or other path-like environment variables, ensure you use absolute paths or paths relative to where the client is run, as variable expansion like `${workspaceFolder}` is not automatically handled by this client's configuration loader.*

### Node.js Server

```json
{
  "context_servers": {
    "NodeServer": {
      "command": {
        "path": "node",
        "args": ["path/to/server.js"],
        "env": {
          "NODE_ENV": "development"
        }
      }
    }
  }
}
```

### Executable Server

```json
{
  "context_servers": {
    "BinaryServer": {
      "command": {
        "path": "path/to/server_executable",
        "args": ["--port", "8080"],
        "env": {}
      }
    }
  }
}
```

## Environment Variables in Configuration

The `env` section within a server's `command` configuration allows you to specify environment variables that will be set for the server process when it's launched by the MCP Client. The client takes these key-value pairs and adds them to the environment that the server subprocess inherits. If a variable specified in the configuration already exists in the client's environment, the value from the configuration will typically override it for the subprocess.

## Path Normalization

The configuration system automatically normalizes file paths specified in the `command.path` for the current operating system. This means you can use forward slashes (`/`) in your paths, and they will be converted to backslashes (`\`) on Windows automatically. For paths within the `env` section, ensure they are correctly formatted for the target OS or use absolute paths.

## Configuration Loading

The client loads configurations in the following order:

1. Explicit configuration dictionary passed to the constructor
2. Configuration file path passed to the constructor
3. Default location (if implemented - *currently not implemented*)

```python
# Load from dictionary
config_dict = {...}
client = MCPClient(config_dict=config_dict)

# Load from file path
client = MCPClient(config_path="path/to/config.json")
```

## Best Practices

1. **Use Separate Config Files**: Maintain different config files for development and production environments.
2. **Environment Variables**: Use the `env` block in the configuration for server-specific environment variables. For sensitive information like API keys that the *client itself* needs (not the server it launches), manage them through your system's environment variables and load them in your client application code (e.g., using `python-dotenv`).
3. **Path Variables**: Use relative paths for `command.path` where possible to make configs portable, or absolute paths for clarity.
4. **Version Control**: Include example config files in version control, not actual configs with secrets.
5. **Validation**: Validate your config file format before deploying.

## Common Issues

### Server Not Found

If you get a "Server not found" error, check:
1. The server name in your code matches exactly the name in the config file.
2. The config file path is correct.

### Connection Failed

If the connection fails, check:
1. The executable `path` in the `command` section is correct and the executable is runnable.
2. All required environment variables for the server are correctly set in the `env` section or in the system environment.
3. The server implements the MCP protocol correctly.

### Tool Not Available

If a tool is not available, check:
1. The server is correctly initialized.
2. The tool is registered with the MCP server.
3. The server is returning the tool in the initialization response.
