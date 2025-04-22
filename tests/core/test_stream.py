"""Tests for the streaming functionality."""

import json
import time
from unittest.mock import Mock

import pytest

from block_agents.core.errors import BlockAgentError
from block_agents.core.stream import StreamEvent, StreamManager


def test_stream_event_init():
    """Test initializing a StreamEvent."""
    event = StreamEvent(
        event_type="test_event",
        pipeline_id="test_pipeline",
        block_id="test_block",
        data={"key": "value"},
        timestamp=1234567890.0,
    )
    
    assert event.event_type == "test_event"
    assert event.pipeline_id == "test_pipeline"
    assert event.block_id == "test_block"
    assert event.data == {"key": "value"}
    assert event.timestamp == 1234567890.0
    
    # Test with default timestamp
    event = StreamEvent(
        event_type="test_event",
        pipeline_id="test_pipeline",
        block_id="test_block",
        data={"key": "value"},
    )
    
    assert event.timestamp > 0  # Should have a timestamp


def test_stream_event_to_dict():
    """Test converting a StreamEvent to a dictionary."""
    event = StreamEvent(
        event_type="test_event",
        pipeline_id="test_pipeline",
        block_id="test_block",
        data={"key": "value"},
        timestamp=1234567890.0,
    )
    
    event_dict = event.to_dict()
    assert event_dict["event_type"] == "test_event"
    assert event_dict["pipeline_id"] == "test_pipeline"
    assert event_dict["block_id"] == "test_block"
    assert event_dict["data"] == {"key": "value"}
    assert event_dict["timestamp"] == 1234567890.0


def test_stream_event_to_json():
    """Test converting a StreamEvent to JSON."""
    event = StreamEvent(
        event_type="test_event",
        pipeline_id="test_pipeline",
        block_id="test_block",
        data={"key": "value"},
        timestamp=1234567890.0,
    )
    
    event_json = event.to_json()
    assert isinstance(event_json, str)
    
    # Verify the JSON can be parsed back to a dictionary
    event_dict = json.loads(event_json)
    assert event_dict["event_type"] == "test_event"


def test_stream_event_to_sse():
    """Test converting a StreamEvent to SSE format."""
    event = StreamEvent(
        event_type="test_event",
        pipeline_id="test_pipeline",
        block_id="test_block",
        data={"key": "value"},
        timestamp=1234567890.0,
    )
    
    sse = event.to_sse()
    assert sse.startswith("event: test_event\ndata: ")
    assert sse.endswith("\n\n")


def test_stream_event_from_dict():
    """Test creating a StreamEvent from a dictionary."""
    event_dict = {
        "event_type": "test_event",
        "pipeline_id": "test_pipeline",
        "block_id": "test_block",
        "data": {"key": "value"},
        "timestamp": 1234567890.0,
    }
    
    event = StreamEvent.from_dict(event_dict)
    assert event.event_type == "test_event"
    assert event.pipeline_id == "test_pipeline"
    assert event.block_id == "test_block"
    assert event.data == {"key": "value"}
    assert event.timestamp == 1234567890.0


def test_stream_event_from_json():
    """Test creating a StreamEvent from JSON."""
    event_json = json.dumps({
        "event_type": "test_event",
        "pipeline_id": "test_pipeline",
        "block_id": "test_block",
        "data": {"key": "value"},
        "timestamp": 1234567890.0,
    })
    
    event = StreamEvent.from_json(event_json)
    assert event.event_type == "test_event"
    assert event.pipeline_id == "test_pipeline"
    assert event.block_id == "test_block"
    assert event.data == {"key": "value"}
    assert event.timestamp == 1234567890.0


def test_stream_manager_init():
    """Test initializing a StreamManager."""
    sm = StreamManager(
        pipeline_id="test_pipeline",
        enabled=True,
        log_level="info",
        include_block_types=["llm", "text"],
        throttle_ms=200,
    )
    
    assert sm.pipeline_id == "test_pipeline"
    assert sm.enabled is True
    assert sm.log_level == "info"
    assert sm.include_block_types == ["llm", "text"]
    assert sm.throttle_ms == 200
    assert sm.subscribers == []
    assert sm._last_event_time == {}


def test_stream_manager_add_remove_subscriber():
    """Test adding and removing subscribers."""
    sm = StreamManager(pipeline_id="test_pipeline")
    subscriber = Mock()
    
    # Add a subscriber
    sm.add_subscriber(subscriber)
    assert subscriber in sm.subscribers
    
    # Add the same subscriber again (should not duplicate)
    sm.add_subscriber(subscriber)
    assert len(sm.subscribers) == 1
    
    # Remove the subscriber
    sm.remove_subscriber(subscriber)
    assert subscriber not in sm.subscribers
    
    # Remove a non-existent subscriber (should not raise an error)
    sm.remove_subscriber(Mock())


def test_stream_manager_emit():
    """Test emitting events."""
    sm = StreamManager(pipeline_id="test_pipeline")
    subscriber = Mock()
    sm.add_subscriber(subscriber)
    
    # Emit an event
    sm.emit("test_event", "test_block", {"key": "value"})
    
    # Verify the subscriber was called
    assert subscriber.call_count == 1
    
    # Verify the event data
    event = subscriber.call_args[0][0]
    assert event.event_type == "test_event"
    assert event.pipeline_id == "test_pipeline"
    assert event.block_id == "test_block"
    assert event.data == {"key": "value"}


def test_stream_manager_throttling():
    """Test event throttling."""
    sm = StreamManager(pipeline_id="test_pipeline", throttle_ms=500)
    subscriber = Mock()
    sm.add_subscriber(subscriber)
    
    # Emit the first event
    sm.emit("test_event", "test_block", {"key": "value1"})
    assert subscriber.call_count == 1
    
    # Emit the same event immediately (should be throttled)
    sm.emit("test_event", "test_block", {"key": "value2"})
    assert subscriber.call_count == 1  # Still 1, not 2
    
    # Wait for the throttle interval and emit again
    sm._last_event_time = {}  # Reset throttling to simulate time passing
    sm.emit("test_event", "test_block", {"key": "value3"})
    assert subscriber.call_count == 2


def test_stream_manager_log_level_filtering():
    """Test filtering events by log level."""
    sm = StreamManager(pipeline_id="test_pipeline", log_level="warning")
    subscriber = Mock()
    sm.add_subscriber(subscriber)
    
    # Emit a debug event (should be filtered out)
    sm.emit("debug_event", "test_block", {"key": "value"}, level="debug")
    assert subscriber.call_count == 0
    
    # Emit an info event (should be filtered out)
    sm.emit("info_event", "test_block", {"key": "value"}, level="info")
    assert subscriber.call_count == 0
    
    # Emit a warning event (should pass through)
    sm.emit("warning_event", "test_block", {"key": "value"}, level="warning")
    assert subscriber.call_count == 1
    
    # Emit an error event (should pass through)
    sm.emit("error_event", "test_block", {"key": "value"}, level="error")
    assert subscriber.call_count == 2


def test_stream_manager_block_type_filtering():
    """Test filtering events by block type."""
    sm = StreamManager(pipeline_id="test_pipeline", include_block_types=["text", "llm"])
    subscriber = Mock()
    sm.add_subscriber(subscriber)
    
    # Emit an event for an included block type
    sm.emit("test_event", "text_block", {"key": "value"})
    assert subscriber.call_count == 1
    
    # Emit an event for an included block type
    sm.emit("test_event", "llm_block", {"key": "value"})
    assert subscriber.call_count == 2
    
    # Emit an event for a non-included block type
    sm.emit("test_event", "file_block", {"key": "value"})
    assert subscriber.call_count == 2  # Still 2, not 3


def test_stream_manager_emit_convenience_methods():
    """Test convenience methods for emitting common events."""
    sm = StreamManager(pipeline_id="test_pipeline")
    subscriber = Mock()
    sm.add_subscriber(subscriber)
    
    # Test emit_error
    error = BlockAgentError("Test error")
    sm.emit_error("test_block", error)
    event = subscriber.call_args[0][0]
    assert event.event_type == "block_error"
    assert event.block_id == "test_block"
    assert "message" in event.data
    assert event.data["type"] == "BlockAgentError"
    
    # Test emit_start
    subscriber.reset_mock()
    sm.emit_start("test_block", {"option": "value"})
    event = subscriber.call_args[0][0]
    assert event.event_type == "block_start"
    assert event.block_id == "test_block"
    assert "message" in event.data
    assert "config" in event.data
    
    # Test emit_progress
    subscriber.reset_mock()
    sm.emit_progress("test_block", 0.5, "partial result")
    event = subscriber.call_args[0][0]
    assert event.event_type == "block_progress"
    assert event.block_id == "test_block"
    assert event.data["progress"] == 0.5
    assert event.data["partial_result"] == "partial result"
    
    # Test emit_complete
    subscriber.reset_mock()
    sm.emit_complete("test_block", "final result")
    event = subscriber.call_args[0][0]
    assert event.event_type == "block_complete"
    assert event.block_id == "test_block"
    assert event.data["result"] == "final result"
    
    # Test emit_log
    subscriber.reset_mock()
    sm.emit_log("test_block", "log message", "warning")
    event = subscriber.call_args[0][0]
    assert event.event_type == "block_log"
    assert event.block_id == "test_block"
    assert event.data["message"] == "log message"
    assert event.data["level"] == "warning"