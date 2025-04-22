"""Configuration management for the block-based agentic pipeline system."""

import argparse
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from dotenv import load_dotenv

from block_agents.core.errors import ConfigurationError


class Config:
    """Configuration manager for the block-based agentic pipeline system.

    This class handles configuration from multiple sources with the following precedence:
    1. Command-line arguments
    2. Environment variables
    3. Configuration file
    4. Default values
    """

    # Default configuration values
    DEFAULTS = {
        "log_level": "info",
        "max_pipeline_runtime_seconds": 3600,
        "temp_directory": "/tmp/block_agents",
        "llm": {
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "default_model": "gpt-4",
                    "timeout_seconds": 60,
                },
                "anthropic": {
                    "default_model": "claude-3-opus",
                    "timeout_seconds": 120,
                },
                "cohere": {
                    "default_model": "command-r",
                    "timeout_seconds": 30,
                },
                "local": {
                    "endpoint": "http://localhost:8000/v1",
                    "default_model": "local-model",
                },
            },
        },
        "storage": {
            "type": "filesystem",
            "path": "./data",
        },
        "api": {
            "host": "0.0.0.0",
            "port": 8080,
            "cors_origins": ["http://localhost:3000"],
        },
        "streaming": {
            "enabled": True,
            "buffer_size": 1024,
            "max_clients": 100,
        },
    }

    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize a new Config instance.

        Args:
            config_dict: Configuration dictionary
        """
        self._config = config_dict

    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "Config":
        """Load configuration from all sources.

        Args:
            config_path: Path to a configuration file (optional)

        Returns:
            A Config instance with merged configuration

        Raises:
            ConfigurationError: If there's an error loading the configuration
        """
        # Start with default values
        config = cls.DEFAULTS.copy()

        # Load environment variables
        load_dotenv()
        env_config = cls._load_from_env()
        cls._deep_update(config, env_config)

        # Load from configuration file if provided
        if config_path:
            file_config = cls._load_from_file(config_path)
            cls._deep_update(config, file_config)

        # Load from command-line arguments
        cmd_config = cls._load_from_args()
        cls._deep_update(config, cmd_config)

        return cls(config)

    @staticmethod
    def _load_from_file(config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from a file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: If there's an error loading the file
        """
        path = Path(config_path)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                if path.suffix.lower() in (".yaml", ".yml"):
                    config = yaml.safe_load(f)
                elif path.suffix.lower() == ".json":
                    import json
                    config = json.load(f)
                else:
                    raise ConfigurationError(
                        f"Unsupported configuration file format: {path.suffix}"
                    )
            return config.get("block_agents", {}) if config else {}
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration file: {e}")

    @staticmethod
    def _load_from_env() -> Dict[str, Any]:
        """Load configuration from environment variables.

        Environment variables with the prefix BLOCK_AGENTS_ are used.
        Nested keys are separated by underscores, e.g. BLOCK_AGENTS_LLM_DEFAULT_PROVIDER.

        Returns:
            Configuration dictionary
        """
        prefix = "BLOCK_AGENTS_"
        result: Dict[str, Any] = {}

        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split("_")
                current = result
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = Config._parse_env_value(value)

        return result

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse an environment variable value to the appropriate type.

        Args:
            value: The environment variable value

        Returns:
            The parsed value
        """
        # Check for boolean values
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Check for integer values
        try:
            return int(value)
        except ValueError:
            pass

        # Check for float values
        try:
            return float(value)
        except ValueError:
            pass

        # Check for list values (comma-separated)
        if "," in value:
            return [Config._parse_env_value(v.strip()) for v in value.split(",")]

        # Default to string
        return value

    @staticmethod
    def _load_from_args() -> Dict[str, Any]:
        """Load configuration from command-line arguments.

        Returns:
            Configuration dictionary
        """
        parser = argparse.ArgumentParser(description="Block Agent Pipeline System")
        parser.add_argument("--log-level", help="Logging level")
        parser.add_argument("--config", help="Path to configuration file")
        parser.add_argument("--port", type=int, help="API server port")
        parser.add_argument("--host", help="API server host")
        parser.add_argument("--temp-dir", help="Temporary directory path")
        parser.add_argument("--llm-provider", help="Default LLM provider")
        parser.add_argument("--disable-streaming", action="store_true", help="Disable streaming")

        # Parse known args to avoid errors on unknown arguments
        args, _ = parser.parse_known_args()
        result: Dict[str, Any] = {}

        if args.log_level:
            result["log_level"] = args.log_level

        if args.port:
            if "api" not in result:
                result["api"] = {}
            result["api"]["port"] = args.port

        if args.host:
            if "api" not in result:
                result["api"] = {}
            result["api"]["host"] = args.host

        if args.temp_dir:
            result["temp_directory"] = args.temp_dir

        if args.llm_provider:
            if "llm" not in result:
                result["llm"] = {}
            result["llm"]["default_provider"] = args.llm_provider

        if args.disable_streaming:
            if "streaming" not in result:
                result["streaming"] = {}
            result["streaming"]["enabled"] = False

        return result

    @staticmethod
    def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively update a nested dictionary.

        Args:
            target: The dictionary to update
            source: The dictionary with updates
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                Config._deep_update(target[key], value)
            else:
                target[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by its key path.

        Args:
            key_path: Dot-separated path to the configuration value
            default: Default value to return if the key is not found

        Returns:
            The configuration value, or the default value if not found
        """
        keys = key_path.split(".")
        current = self._config

        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]

        return current

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get an API key for a specific provider.

        Args:
            provider: The provider name (e.g., "openai", "anthropic")

        Returns:
            The API key, or None if not found

        Raises:
            ConfigurationError: If the API key is required but not found
        """
        # Check environment variables first with priority
        env_var = f"BLOCK_AGENTS_LLM_PROVIDERS_{provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var)

        if not api_key:
            # Try the configuration
            api_key = self.get(f"llm.providers.{provider}.api_key")

        return api_key

    def as_dict(self) -> Dict[str, Any]:
        """Get the full configuration as a dictionary.

        Returns:
            The configuration dictionary
        """
        return self._config.copy()

    def resolve_env_vars(self, value: str) -> str:
        """Resolve environment variables in a configuration value.

        Args:
            value: The configuration value with potential environment variables

        Returns:
            The resolved value
        """
        if not isinstance(value, str):
            return value

        pattern = r"\${([^}]+)}"
        matches = re.findall(pattern, value)

        result = value
        for match in matches:
            env_value = os.environ.get(match)
            if env_value is not None:
                result = result.replace(f"${{{match}}}", env_value)

        return result
    
    def validate(self) -> List[str]:
        """Validate the configuration.

        Returns:
            A list of validation errors, empty if valid
        """
        errors = []
        
        # Check log level
        valid_log_levels = {"debug", "info", "warning", "error"}
        log_level = self.get("log_level")
        if log_level not in valid_log_levels:
            errors.append(f"Invalid log level: {log_level}. Must be one of {valid_log_levels}")
            
        # Check LLM provider configuration
        default_provider = self.get("llm.default_provider")
        providers = self.get("llm.providers", {})
        
        if default_provider and default_provider not in providers:
            errors.append(f"Default LLM provider '{default_provider}' not found in providers")
            
        for provider, provider_config in providers.items():
            if provider != "local" and not self.get_api_key(provider):
                errors.append(f"API key not found for LLM provider: {provider}")
                
        # Check API configuration
        api_port = self.get("api.port")
        if api_port and (not isinstance(api_port, int) or api_port < 1 or api_port > 65535):
            errors.append(f"Invalid API port: {api_port}. Must be between 1 and 65535")
            
        # Check storage configuration
        storage_type = self.get("storage.type")
        valid_storage_types = {"filesystem", "s3", "database"}
        if storage_type not in valid_storage_types:
            errors.append(f"Invalid storage type: {storage_type}. Must be one of {valid_storage_types}")
            
        return errors