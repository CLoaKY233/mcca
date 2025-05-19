# mcpclient/config.py
import json
import os
from typing import Dict, Any, Optional

class Config:
    """Configuration manager for MCP client"""

    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize configuration

        Args:
            config_path: Path to JSON config file
            config_dict: Dictionary containing configuration
        """
        self.config: Dict[str, Any] = {}

        if config_dict:
            self.config = config_dict
        elif config_path:
            self.load_from_file(config_path)

    def load_from_file(self, path: str) -> None:
        """Load configuration from file

        Args:
            path: Path to the configuration file

        Raises:
            ValueError: If file cannot be read or parsed
        """
        try:
            with open(path, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading config file: {str(e)}")

    def get_server_config(self, server_name: str) -> Dict[str, Any]:
        """Get configuration for a specific server

        Args:
            server_name: Name of the server

        Returns:
            Server configuration dictionary

        Raises:
            ValueError: If server not found
        """
        if "context_servers" not in self.config or server_name not in self.config["context_servers"]:
            raise ValueError(f"Server '{server_name}' not found in config")

        return self.config["context_servers"][server_name]

    def get_server_names(self) -> list[str]:
        """Get list of all server names in config

        Returns:
            List of server names
        """
        if "context_servers" not in self.config:
            return []

        return list(self.config["context_servers"].keys())

    def normalize_env_variables(self, env: Dict[str, Any]) -> Dict[str, str]:
        """Normalize environment variables

        Args:
            env: Environment variables dictionary

        Returns:
            Normalized environment variables
        """
        # Convert env dict to proper environment variables
        environment = os.environ.copy()
        if env:
            # Make sure all paths use correct format for the platform
            normalized_env = {}
            for key, value in env.items():
                if isinstance(value, str) and os.path.sep in value:
                    normalized_env[key] = os.path.normpath(value)
                else:
                    normalized_env[key] = str(value)

            environment.update(normalized_env)

        return environment
