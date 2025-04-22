"""Context management for the block-based agentic pipeline system."""

from typing import Any, Dict, Optional

from block_agents.core.config import Config
from block_agents.core.stream import StreamManager


class Context:
    """Execution context for a pipeline run.

    This class provides access to:
    - Pipeline state and variables
    - Stream manager for event emission
    - LLM client manager
    - Configuration
    """

    def __init__(
        self,
        pipeline_id: str,
        config: Config,
        stream_manager: Optional[StreamManager] = None,
        global_values: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Context.

        Args:
            pipeline_id: ID of the pipeline being executed
            config: Configuration instance
            stream_manager: Stream manager for event emission
            global_values: Initial global values
        """
        self.pipeline_id = pipeline_id
        self.config = config
        self._global_values = global_values or {}
        self._block_values = {}
        
        # Create a stream manager if one wasn't provided
        if stream_manager is None:
            self._stream_manager = StreamManager(
                pipeline_id=pipeline_id,
                enabled=config.get("streaming.enabled", True),
                log_level=config.get("log_level", "info"),
                include_block_types=config.get("streaming.include_block_types", []),
                throttle_ms=config.get("streaming.throttle_ms", 100),
            )
        else:
            self._stream_manager = stream_manager

        # LLM client manager will be set by the pipeline engine
        self._client_manager = None

    def get_stream_manager(self) -> StreamManager:
        """Get the stream manager.

        Returns:
            The stream manager
        """
        return self._stream_manager

    def get_global_value(self, key: str, default: Any = None) -> Any:
        """Get a global value.

        Args:
            key: The key
            default: Default value to return if the key is not found

        Returns:
            The value, or the default value if not found
        """
        return self._global_values.get(key, default)

    def set_global_value(self, key: str, value: Any) -> None:
        """Set a global value.

        Args:
            key: The key
            value: The value
        """
        self._global_values[key] = value

    def get_all_global_values(self) -> Dict[str, Any]:
        """Get all global values.

        Returns:
            Dictionary of all global values
        """
        return self._global_values.copy()

    def get_block_value(self, block_id: str, default: Any = None) -> Any:
        """Get a block's output value.

        Args:
            block_id: ID of the block
            default: Default value to return if the block's output is not found

        Returns:
            The block's output value, or the default value if not found
        """
        return self._block_values.get(block_id, default)

    def set_block_value(self, block_id: str, value: Any) -> None:
        """Set a block's output value.

        Args:
            block_id: ID of the block
            value: The output value
        """
        self._block_values[block_id] = value

    def get_all_block_values(self) -> Dict[str, Any]:
        """Get all block values.

        Returns:
            Dictionary of all block values
        """
        return self._block_values.copy()

    def set_client_manager(self, client_manager: Any) -> None:
        """Set the LLM client manager.

        Args:
            client_manager: The LLM client manager
        """
        self._client_manager = client_manager

    def get_client_manager(self) -> Any:
        """Get the LLM client manager.

        Returns:
            The LLM client manager, or None if not set
        """
        return self._client_manager

    def get_temp_directory(self) -> str:
        """Get the temporary directory path.

        Returns:
            The temporary directory path
        """
        return self.config.get("temp_directory", "/tmp/block_agents")

    def get_max_runtime_seconds(self) -> int:
        """Get the maximum pipeline runtime in seconds.

        Returns:
            The maximum pipeline runtime in seconds
        """
        return self.config.get("max_pipeline_runtime_seconds", 3600)

    def log(self, block_id: str, message: str, level: str = "info") -> None:
        """Log a message to the stream.

        Args:
            block_id: ID of the block
            message: The message
            level: Log level (debug, info, warning, error)
        """
        self._stream_manager.emit_log(block_id, message, level)

    def clone(self) -> "Context":
        """Create a clone of this context.

        Returns:
            A new Context instance with the same configuration
        """
        return Context(
            pipeline_id=self.pipeline_id,
            config=self.config,
            stream_manager=self._stream_manager,
            global_values=self._global_values.copy(),
        )