"""Tests for the Block base class."""

import time
from typing import Any, Dict

import pytest

from block_agents.core.block import Block, BlockFactory
from block_agents.core.context import Context
from block_agents.core.errors import (
    BlockRuntimeError,
    InputValidationError,
    OutputValidationError,
    TimeoutError,
)
from block_agents.core.stream import StreamManager


# Define a simple test block
class TestBlock(Block):
    """Test block implementation."""
    
    def process(self, inputs: Dict[str, Any], context: Context) -> Any:
        """Process inputs and return result."""
        # Add a small delay for timeout testing
        if inputs.get("delay"):
            time.sleep(inputs["delay"])
        
        # Return inputs as outputs
        return inputs.get("value", "default_result")
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate inputs."""
        if inputs.get("fail_validation"):
            raise InputValidationError("Input validation failed")
    
    def validate_output(self, output: Any) -> None:
        """Validate output."""
        if output == "invalid_output":
            raise OutputValidationError("Output validation failed")
    
    def get_required_inputs(self) -> set:
        """Get required inputs."""
        return {"required_input"}
    
    def get_optional_inputs(self) -> set:
        """Get optional inputs."""
        return {"optional_input"}
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default config."""
        return {
            "timeout_seconds": 30,
            "custom_setting": "test_value",
        }
    
    def get_description(self) -> str:
        """Get block description."""
        return "Test block for testing"


@pytest.fixture
def context(monkeypatch):
    """Create a mock context for testing."""
    from block_agents.core.config import Config
    from block_agents.core.stream import StreamManager
    
    # Mock StreamManager methods to avoid actual streaming
    monkeypatch.setattr(StreamManager, "emit_start", lambda self, block_id, config: None)
    monkeypatch.setattr(StreamManager, "emit_complete", lambda self, block_id, result: None)
    monkeypatch.setattr(StreamManager, "emit_error", lambda self, block_id, error: None)
    monkeypatch.setattr(StreamManager, "emit_progress", lambda self, block_id, progress, partial_result=None: None)
    monkeypatch.setattr(StreamManager, "emit_log", lambda self, block_id, message, level: None)
    
    return Context(
        pipeline_id="test-pipeline",
        config=Config({"log_level": "info"})
    )


class TestBlockClass:
    """Tests for the Block base class."""
    
    def test_init(self):
        """Test block initialization."""
        block_id = "test_block"
        config = {"timeout_seconds": 120, "custom_setting": "custom_value"}
        
        block = TestBlock(block_id, config)
        
        assert block.id == block_id
        assert block.config == config
        assert block.timeout == 120
    
    def test_execute_success(self, context):
        """Test successful block execution."""
        block = TestBlock("test_block", {})
        result = block.execute({"value": "test_value"}, context)
        
        assert result == "test_value"
    
    def test_execute_input_validation_error(self, context):
        """Test block execution with input validation error."""
        block = TestBlock("test_block", {})
        
        with pytest.raises(InputValidationError) as excinfo:
            block.execute({"fail_validation": True}, context)
        
        assert "Input validation failed" in str(excinfo.value)
    
    def test_execute_output_validation_error(self, context):
        """Test block execution with output validation error."""
        block = TestBlock("test_block", {})
        
        with pytest.raises(OutputValidationError) as excinfo:
            block.execute({"value": "invalid_output"}, context)
        
        assert "Output validation failed" in str(excinfo.value)
    
    def test_execute_timeout(self, context):
        """Test block execution timeout."""
        block = TestBlock("test_block", {"timeout_seconds": 0.1})
        
        with pytest.raises(TimeoutError) as excinfo:
            block.execute({"delay": 0.2, "value": "test_value"}, context)
        
        assert "Block execution exceeded timeout" in str(excinfo.value)
    
    def test_execute_runtime_error(self, context, monkeypatch):
        """Test block execution with runtime error."""
        # Mock the process method to raise an exception
        def mock_process(self, inputs, context):
            raise RuntimeError("Process error")
        
        monkeypatch.setattr(TestBlock, "process", mock_process)
        
        block = TestBlock("test_block", {})
        
        with pytest.raises(RuntimeError) as excinfo:
            block.execute({}, context)
        
        assert "Process error" in str(excinfo.value)
    
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = TestBlock("test_block", {})
        assert block.get_required_inputs() == {"required_input"}
    
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = TestBlock("test_block", {})
        assert block.get_optional_inputs() == {"optional_input"}
    
    def test_get_default_config(self):
        """Test getting default config."""
        block = TestBlock("test_block", {})
        assert block.get_default_config() == {
            "timeout_seconds": 30,
            "custom_setting": "test_value",
        }
    
    def test_get_description(self):
        """Test getting block description."""
        block = TestBlock("test_block", {})
        assert block.get_description() == "Test block for testing"
    
    def test_report_progress(self, context, monkeypatch):
        """Test reporting progress."""
        # Mock the emit_progress method to track calls
        calls = []
        def mock_emit_progress(self, block_id, progress, partial_result=None):
            calls.append((block_id, progress, partial_result))
        
        monkeypatch.setattr(StreamManager, "emit_progress", mock_emit_progress)
        
        block = TestBlock("test_block", {})
        
        # Test with valid progress value
        block.report_progress(context, 0.5, "partial")
        assert calls == [("test_block", 0.5, "partial")]
        
        # Test with invalid progress value (should not call emit_progress)
        calls.clear()
        block.report_progress(context, 1.5, "invalid")
        assert calls == []
    
    def test_log(self, context, monkeypatch):
        """Test logging."""
        # Mock the emit_log method to track calls
        calls = []
        def mock_emit_log(self, block_id, message, level):
            calls.append((block_id, message, level))
        
        monkeypatch.setattr(StreamManager, "emit_log", mock_emit_log)
        
        block = TestBlock("test_block", {})
        
        # Test with default log level
        block.log(context, "Test message")
        assert calls == [("test_block", "Test message", "info")]
        
        # Test with custom log level
        calls.clear()
        block.log(context, "Debug message", "debug")
        assert calls == [("test_block", "Debug message", "debug")]


class TestBlockFactory:
    """Tests for the BlockFactory class."""
    
    def test_create_block(self, monkeypatch):
        """Test creating a block instance."""
        # Mock BlockRegistry.get to return TestBlock
        def mock_get(block_type):
            return TestBlock
        
        monkeypatch.setattr("block_agents.core.registry.BlockRegistry.get", mock_get)
        
        # Create a block instance
        block = BlockFactory.create_block("test_block", "test_instance", {"timeout_seconds": 60})
        
        assert isinstance(block, TestBlock)
        assert block.id == "test_instance"
        assert block.config == {"timeout_seconds": 60}
    
    def test_create_block_error(self, monkeypatch):
        """Test error when creating a block instance."""
        # Mock BlockRegistry.get to raise an exception
        def mock_get(block_type):
            raise ValueError("Registry error")
        
        monkeypatch.setattr("block_agents.core.registry.BlockRegistry.get", mock_get)
        
        # Attempt to create a block instance
        with pytest.raises(ValueError) as excinfo:
            BlockFactory.create_block("test_block", "test_instance", {})
        
        assert "Registry error" in str(excinfo.value)