"""Tests for the Context class."""

import pytest

from block_agents.core.config import Config
from block_agents.core.context import Context
from block_agents.core.stream import StreamManager


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config({
        "log_level": "info",
        "max_pipeline_runtime_seconds": 120,
        "temp_directory": "/tmp/test_block_agents",
        "streaming": {
            "enabled": True,
            "include_block_types": ["test"],
            "throttle_ms": 50
        }
    })


@pytest.fixture
def mock_stream_manager():
    """Create a mock stream manager for testing."""
    return StreamManager(
        pipeline_id="test-pipeline",
        enabled=True,
        log_level="info",
        include_block_types=["test"],
        throttle_ms=50
    )


class TestContext:
    """Tests for the Context class."""

    def test_init(self, mock_config):
        """Test Context initialization."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config
        )
        
        assert context.pipeline_id == "test-pipeline"
        assert context.config == mock_config
        assert context._global_values == {}
        assert context._block_values == {}
        assert context._client_manager is None
        assert isinstance(context._stream_manager, StreamManager)
    
    def test_init_with_stream_manager(self, mock_config, mock_stream_manager):
        """Test Context initialization with a provided stream manager."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config,
            stream_manager=mock_stream_manager
        )
        
        assert context._stream_manager == mock_stream_manager
    
    def test_init_with_global_values(self, mock_config):
        """Test Context initialization with global values."""
        global_values = {"key1": "value1", "key2": 42}
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config,
            global_values=global_values
        )
        
        assert context._global_values == global_values
        assert context.get_global_value("key1") == "value1"
        assert context.get_global_value("key2") == 42
    
    def test_get_stream_manager(self, mock_config, mock_stream_manager):
        """Test getting the stream manager."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config,
            stream_manager=mock_stream_manager
        )
        
        assert context.get_stream_manager() == mock_stream_manager
    
    def test_global_values(self, mock_config):
        """Test getting and setting global values."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config
        )
        
        # Set and get a global value
        context.set_global_value("test_key", "test_value")
        assert context.get_global_value("test_key") == "test_value"
        
        # Get a non-existent value with default
        assert context.get_global_value("non_existent", "default") == "default"
        
        # Get all global values
        context.set_global_value("another_key", 42)
        all_values = context.get_all_global_values()
        assert all_values == {"test_key": "test_value", "another_key": 42}
        
        # Ensure the returned dictionary is a copy
        all_values["new_key"] = "new_value"
        assert "new_key" not in context.get_all_global_values()
    
    def test_block_values(self, mock_config):
        """Test getting and setting block values."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config
        )
        
        # Set and get a block value
        context.set_block_value("block1", "result1")
        assert context.get_block_value("block1") == "result1"
        
        # Get a non-existent value with default
        assert context.get_block_value("non_existent", "default") == "default"
        
        # Get all block values
        context.set_block_value("block2", {"key": "value"})
        all_values = context.get_all_block_values()
        assert all_values == {"block1": "result1", "block2": {"key": "value"}}
        
        # Ensure the returned dictionary is a copy
        all_values["block3"] = "result3"
        assert "block3" not in context.get_all_block_values()
    
    def test_client_manager(self, mock_config):
        """Test getting and setting the client manager."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config
        )
        
        # Initially, client manager should be None
        assert context.get_client_manager() is None
        
        # Set and get the client manager
        mock_client = object()
        context.set_client_manager(mock_client)
        assert context.get_client_manager() is mock_client
    
    def test_get_temp_directory(self, mock_config):
        """Test getting the temporary directory path."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config
        )
        
        assert context.get_temp_directory() == "/tmp/test_block_agents"
    
    def test_get_max_runtime_seconds(self, mock_config):
        """Test getting the maximum pipeline runtime."""
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config
        )
        
        assert context.get_max_runtime_seconds() == 120
    
    def test_log(self, mock_config, mock_stream_manager, monkeypatch):
        """Test the log method."""
        # Mock the emit_log method of StreamManager
        calls = []
        def mock_emit_log(self, block_id, message, level):
            calls.append((block_id, message, level))
        
        monkeypatch.setattr(StreamManager, "emit_log", mock_emit_log)
        
        context = Context(
            pipeline_id="test-pipeline",
            config=mock_config,
            stream_manager=mock_stream_manager
        )
        
        # Test logging with default level
        context.log("test_block", "Test message")
        assert calls == [("test_block", "Test message", "info")]
        
        # Test logging with explicit level
        calls.clear()
        context.log("test_block", "Error message", "error")
        assert calls == [("test_block", "Error message", "error")]
    
    def test_clone(self, mock_config, mock_stream_manager):
        """Test cloning the context."""
        original = Context(
            pipeline_id="test-pipeline",
            config=mock_config,
            stream_manager=mock_stream_manager,
            global_values={"key": "value"}
        )
        
        # Set some values in the original context
        original.set_global_value("another_key", 42)
        original.set_block_value("block1", "result1")
        
        # Clone the context
        clone = original.clone()
        
        # Check that the clone has the same configuration
        assert clone.pipeline_id == original.pipeline_id
        assert clone.config == original.config
        assert clone._stream_manager == original._stream_manager
        assert clone._global_values == original._global_values
        
        # The clone should have the same global values but not block values
        assert clone.get_global_value("key") == "value"
        assert clone.get_global_value("another_key") == 42
        assert clone.get_block_value("block1") is None
        
        # Changes to the clone should not affect the original
        clone.set_global_value("new_key", "new_value")
        assert original.get_global_value("new_key") is None