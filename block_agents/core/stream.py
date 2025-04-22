"""Streaming functionality for the block-based agentic pipeline system."""

import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union

from block_agents.core.errors import BlockAgentError


class StreamEvent:
    """Represents a stream event in the pipeline execution.

    Attributes:
        event_type: Type of the event (e.g., block_start, block_progress, block_complete)
        pipeline_id: ID of the pipeline that generated the event
        block_id: ID of the block that generated the event
        timestamp: Unix timestamp when the event was generated
        data: Additional event data
    """

    def __init__(
        self,
        event_type: str,
        pipeline_id: str,
        block_id: str,
        data: Dict[str, Any],
        timestamp: Optional[float] = None,
    ):
        """Initialize a new StreamEvent.

        Args:
            event_type: Type of the event
            pipeline_id: ID of the pipeline
            block_id: ID of the block
            data: Additional event data
            timestamp: Unix timestamp (default: current time)
        """
        self.event_type = event_type
        self.pipeline_id = pipeline_id
        self.block_id = block_id
        self.data = data
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary.

        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "pipeline_id": self.pipeline_id,
            "block_id": self.block_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    def to_json(self) -> str:
        """Convert the event to a JSON string.

        Returns:
            JSON representation of the event
        """
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """Convert the event to a Server-Sent Events (SSE) format.

        Returns:
            SSE representation of the event
        """
        return f"event: {self.event_type}\ndata: {self.to_json()}\n\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """Create a StreamEvent from a dictionary.

        Args:
            data: Dictionary representation of the event

        Returns:
            A new StreamEvent instance
        """
        return cls(
            event_type=data["event_type"],
            pipeline_id=data["pipeline_id"],
            block_id=data["block_id"],
            data=data["data"],
            timestamp=data.get("timestamp"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "StreamEvent":
        """Create a StreamEvent from a JSON string.

        Args:
            json_str: JSON representation of the event

        Returns:
            A new StreamEvent instance
        """
        return cls.from_dict(json.loads(json_str))


class StreamManager:
    """Manages streaming events during pipeline execution.

    This class handles:
    - Emitting events during pipeline and block execution
    - Subscribing to events via callback functions
    - Throttling events to avoid overwhelming consumers
    """

    def __init__(
        self,
        pipeline_id: str,
        enabled: bool = True,
        log_level: str = "info",
        include_block_types: Optional[List[str]] = None,
        throttle_ms: int = 100,
    ):
        """Initialize a new StreamManager.

        Args:
            pipeline_id: ID of the pipeline being executed
            enabled: Whether streaming is enabled
            log_level: Minimum log level to emit (debug, info, warning, error)
            include_block_types: List of block types to include in the stream
            throttle_ms: Throttle events with the same type/block to this interval
        """
        self.pipeline_id = pipeline_id
        self.enabled = enabled
        self.log_level = log_level
        self.include_block_types = include_block_types or []
        self.throttle_ms = throttle_ms
        self.subscribers: List[Callable[[StreamEvent], None]] = []
        
        # For throttling
        self._last_event_time: Dict[str, float] = {}

    def emit(
        self, event_type: str, block_id: str, data: Dict[str, Any], level: str = "info"
    ) -> None:
        """Emit a stream event.

        Args:
            event_type: Type of the event
            block_id: ID of the block that generated the event
            data: Additional event data
            level: Log level of the event (debug, info, warning, error)
        """
        if not self.enabled:
            return

        # Check log level
        log_levels = {"debug": 0, "info": 1, "warning": 2, "error": 3}
        if log_levels.get(level, 0) < log_levels.get(self.log_level, 1):
            return

        # Check block type inclusion
        if self.include_block_types and block_id.split("_")[0] not in self.include_block_types:
            return

        # Check throttling
        key = f"{event_type}:{block_id}"
        now = time.time()
        if key in self._last_event_time:
            elapsed_ms = (now - self._last_event_time[key]) * 1000
            if elapsed_ms < self.throttle_ms:
                return

        self._last_event_time[key] = now

        # Create and emit the event
        event = StreamEvent(
            event_type=event_type,
            pipeline_id=self.pipeline_id,
            block_id=block_id,
            data=data,
        )

        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception as e:
                # Don't fail the pipeline if a subscriber fails
                print(f"Error in stream subscriber: {e}")

    def add_subscriber(self, subscriber: Callable[[StreamEvent], None]) -> None:
        """Add a subscriber to receive stream events.

        Args:
            subscriber: Callback function to receive events
        """
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)

    def remove_subscriber(self, subscriber: Callable[[StreamEvent], None]) -> None:
        """Remove a subscriber.

        Args:
            subscriber: Callback function to remove
        """
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)

    def emit_error(self, block_id: str, error: Union[str, Exception]) -> None:
        """Emit an error event.

        Args:
            block_id: ID of the block that generated the error
            error: The error message or exception
        """
        if isinstance(error, Exception):
            error_data = {
                "message": str(error),
                "type": error.__class__.__name__,
            }
            
            if isinstance(error, BlockAgentError):
                error_data.update(error.to_dict())
        else:
            error_data = {
                "message": error,
                "type": "Error",
            }

        self.emit("block_error", block_id, error_data, level="error")

    def emit_start(self, block_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Emit a block start event.

        Args:
            block_id: ID of the block that started
            config: Block configuration
        """
        data = {"message": f"Starting block {block_id}"}
        if config:
            # Filter out sensitive config values
            safe_config = {k: v for k, v in config.items() if not k.endswith("_key")}
            data["config"] = safe_config

        self.emit("block_start", block_id, data)

    def emit_progress(
        self, block_id: str, progress: float, partial_result: Optional[Any] = None
    ) -> None:
        """Emit a block progress event.

        Args:
            block_id: ID of the block
            progress: Progress value between 0 and 1
            partial_result: Partial result if available
        """
        data = {"progress": progress}
        if partial_result is not None:
            data["partial_result"] = partial_result

        self.emit("block_progress", block_id, data)

    def emit_complete(self, block_id: str, result: Optional[Any] = None) -> None:
        """Emit a block completion event.

        Args:
            block_id: ID of the block
            result: Block result if available
        """
        data = {"message": f"Block {block_id} completed"}
        if result is not None:
            data["result"] = result

        self.emit("block_complete", block_id, data)

    def emit_log(self, block_id: str, message: str, level: str = "info") -> None:
        """Emit a log event.

        Args:
            block_id: ID of the block
            message: Log message
            level: Log level
        """
        data = {"message": message, "level": level}
        self.emit("block_log", block_id, data, level=level)

    def clear(self) -> None:
        """Clear all subscribers and throttling state."""
        self.subscribers.clear()
        self._last_event_time.clear()