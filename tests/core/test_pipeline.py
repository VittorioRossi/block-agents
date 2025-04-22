"""Tests for the Pipeline class."""

import json
import time
from typing import Any, Dict

import pytest

from block_agents.core.block import Block
from block_agents.core.config import Config
from block_agents.core.errors import (
    BlockRuntimeError,
    PipelineDefinitionError,
    PipelineRuntimeError,
)
from block_agents.core.pipeline import Pipeline
from block_agents.core.registry import BlockRegistry


# Define some test blocks for pipeline testing
class TextInputBlock(Block):
    """Text input block for testing."""
    def process(self, inputs, context):
        return {"text": inputs.get("text", "")}

class ProcessingBlock(Block):
    """Processing block for testing."""
    def process(self, inputs, context):
        text = inputs.get("text", "")
        return {"processed_text": text.upper()}

class OutputBlock(Block):
    """Output block for testing."""
    def process(self, inputs, context):
        return inputs.get("processed_text", "")

class ErrorBlock(Block):
    """Error block for testing."""
    def process(self, inputs, context):
        if inputs.get("raise_error", False):
            raise RuntimeError("Block error")
        return {"result": "success"}

class TimeoutBlock(Block):
    """Timeout block for testing."""
    def process(self, inputs, context):
        delay = inputs.get("delay", 0)
        time.sleep(delay)
        return {"result": "done"}


@pytest.fixture
def setup_registry():
    """Set up the block registry for pipeline testing."""
    # Clear the registry
    BlockRegistry.clear()
    
    # Register test blocks
    BlockRegistry.register("text_input", TextInputBlock)
    BlockRegistry.register("processing", ProcessingBlock)
    BlockRegistry.register("output", OutputBlock)
    BlockRegistry.register("error", ErrorBlock)
    BlockRegistry.register("timeout", TimeoutBlock)
    
    # Return and then clear after the test
    yield
    BlockRegistry.clear()


@pytest.fixture
def valid_pipeline_def():
    """Create a valid pipeline definition for testing."""
    return {
        "pipeline_id": "test_pipeline",
        "name": "Test Pipeline",
        "description": "Pipeline for testing",
        "blocks": [
            {
                "id": "input1",
                "type": "text_input",
                "config": {},
                "next": ["process1"]
            },
            {
                "id": "process1",
                "type": "processing",
                "config": {},
                "next": ["output1"]
            },
            {
                "id": "output1",
                "type": "output",
                "config": {},
                "next": []
            }
        ],
        "output": "output1",
        "stream_config": {
            "enabled": True,
            "log_level": "info"
        }
    }


class TestPipeline:
    """Tests for the Pipeline class."""
    
    def test_init_valid(self, setup_registry, valid_pipeline_def):
        """Test initializing with a valid pipeline definition."""
        pipeline = Pipeline(valid_pipeline_def)
        
        assert pipeline.pipeline_id == "test_pipeline"
        assert pipeline.name == "Test Pipeline"
        assert pipeline.description == "Pipeline for testing"
        assert len(pipeline.blocks) == 3
        assert pipeline.output_block_id == "output1"
        assert pipeline.entry_blocks == ["input1"]
    
    def test_init_invalid(self, setup_registry):
        """Test initializing with invalid pipeline definitions."""
        # Missing blocks
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({})
        assert "Pipeline definition must contain 'blocks'" in str(excinfo.value)
        
        # Blocks not a list
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({"blocks": {}})
        assert "'blocks' must be a list" in str(excinfo.value)
        
        # Block missing ID
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"type": "text_input", "config": {}}
                ]
            })
        assert "Block at index 0 must have an 'id'" in str(excinfo.value)
        
        # Block missing type
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "input1", "config": {}}
                ]
            })
        assert "Block at index 0 must have a 'type'" in str(excinfo.value)
        
        # Duplicate block ID
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "input1", "type": "text_input", "config": {}},
                    {"id": "input1", "type": "text_input", "config": {}}
                ]
            })
        assert "Duplicate block ID: input1" in str(excinfo.value)
        
        # Next not a list
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "input1", "type": "text_input", "config": {}, "next": "process1"}
                ]
            })
        assert "'next' for block input1 must be a list" in str(excinfo.value)
        
        # Non-existent next block
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "input1", "type": "text_input", "config": {}, "next": ["nonexistent"]}
                ]
            })
        assert "Block input1 references non-existent block: nonexistent" in str(excinfo.value)
        
        # Circular dependency
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "block1", "type": "text_input", "config": {}, "next": ["block2"]},
                    {"id": "block2", "type": "processing", "config": {}, "next": ["block1"]}
                ]
            })
        assert "Circular dependency detected" in str(excinfo.value)
        
        # Non-existent output block
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "input1", "type": "text_input", "config": {}}
                ],
                "output": "nonexistent"
            })
        assert "Output block not found: nonexistent" in str(excinfo.value)
        
        # No entry points - commented out as the implementation might be different
        # This can be uncommented when we have the actual implementation
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline({
                "blocks": [
                    {"id": "block1", "type": "text_input", "config": {}, "next": []},
                    {"id": "block2", "type": "processing", "config": {}, "next": []}
                ],
                "block_dependencies": {
                    "block1": ["block2"],
                    "block2": ["block1"]
                }
            })
        assert "Pipeline has no entry points" in str(excinfo.value)
    
    def test_execute(self, setup_registry, valid_pipeline_def):
        """Test executing a pipeline."""
        # Skip this test until we have actual implementations of the blocks

        pipeline = Pipeline(valid_pipeline_def)
        
        # Test with direct input to entry block
        result = pipeline.execute({
            "input1": {"text": "hello world"}
        })
        
        assert result == "HELLO WORLD"
        
        # Test with global parameters
        result = pipeline.execute({
            "global_parameters": {
                "text": "global hello"
            }
        })
        
        assert result == "GLOBAL HELLO"
    
    def test_execute_with_error(self, setup_registry):
        """Test executing a pipeline with an error."""
        # Skip this test until we have actual implementations of the blocks
        pipeline_def = {
            "blocks": [
                {
                    "id": "input1",
                    "type": "text_input",
                    "config": {},
                    "next": ["error1"]
                },
                {
                    "id": "error1",
                    "type": "error",
                    "config": {},
                    "next": []
                }
            ],
            "output": "error1"
        }
        
        pipeline = Pipeline(pipeline_def)
        
        # Test with error in a block
        with pytest.raises(PipelineRuntimeError) as excinfo:
            pipeline.execute({
                "input1": {"text": "hello", "raise_error": True}
            })
        
        assert "Pipeline execution error" in str(excinfo.value)
    
    def test_execute_with_timeout(self, setup_registry, monkeypatch):
        """Test executing a pipeline with a timeout."""
        # Skip this test until we have actual implementations of the blocks
        # Override the get_max_runtime_seconds method to return a small value
        from block_agents.core.context import Context
        monkeypatch.setattr(Context, "get_max_runtime_seconds", lambda self: 0.1)
        
        pipeline_def = {
            "blocks": [
                {
                    "id": "input1",
                    "type": "text_input",
                    "config": {},
                    "next": ["timeout1"]
                },
                {
                    "id": "timeout1",
                    "type": "timeout",
                    "config": {},
                    "next": []
                }
            ],
            "output": "timeout1"
        }
        
        pipeline = Pipeline(pipeline_def)
        
        # Test with a delay that exceeds the max runtime
        with pytest.raises(PipelineRuntimeError) as excinfo:
            pipeline.execute({
                "input1": {"delay": 0.2}
            })
        
        assert "Pipeline execution exceeded maximum runtime" in str(excinfo.value)
    
    def test_subscribers(self, setup_registry, valid_pipeline_def):
        """Test adding and removing subscribers."""
        pipeline = Pipeline(valid_pipeline_def)
        
        # Create a subscriber to collect events
        events = []
        def subscriber(event):
            events.append(event)
        
        # Add the subscriber
        pipeline.add_subscriber(subscriber)
        
        # Execute the pipeline
        pipeline.execute({
            "input1": {"text": "hello"}
        })
        
        # Check that events were collected
        assert len(events) > 0
        
        # Remove the subscriber
        pipeline.remove_subscriber(subscriber)
        
        # Clear events and execute again
        events.clear()
        pipeline.execute({
            "input1": {"text": "hello"}
        })
        
        # Check that no events were collected
        assert len(events) == 0
    
    def test_from_json(self, setup_registry, valid_pipeline_def):
        """Test creating a pipeline from JSON."""
        json_str = json.dumps(valid_pipeline_def)
        pipeline = Pipeline.from_json(json_str)
        
        assert pipeline.pipeline_id == "test_pipeline"
        assert pipeline.name == "Test Pipeline"
        assert len(pipeline.blocks) == 3
        
        # Test with invalid JSON
        with pytest.raises(PipelineDefinitionError) as excinfo:
            Pipeline.from_json("{invalid json")
        assert "Invalid JSON" in str(excinfo.value)
    
    def test_to_json(self, setup_registry, valid_pipeline_def):
        """Test converting a pipeline to JSON."""
        pipeline = Pipeline(valid_pipeline_def)
        json_str = pipeline.to_json()
        
        # Parse the JSON and check that it matches the original definition
        parsed = json.loads(json_str)
        assert parsed["pipeline_id"] == "test_pipeline"
        assert parsed["name"] == "Test Pipeline"
        assert len(parsed["blocks"]) == 3
    
    def test_complex_pipeline(self, setup_registry):
        """Test a more complex pipeline with multiple paths."""
        pipeline_def = {
            "blocks": [
                {
                    "id": "input1",
                    "type": "text_input",
                    "config": {},
                    "next": ["process1", "process2"]
                },
                {
                    "id": "process1",
                    "type": "processing",
                    "config": {},
                    "next": ["output1"]
                },
                {
                    "id": "process2",
                    "type": "processing",
                    "config": {},
                    "next": ["output1"]
                },
                {
                    "id": "output1",
                    "type": "output",
                    "config": {},
                    "next": []
                }
            ],
            "output": "output1"
        }
        
        pipeline = Pipeline(pipeline_def)
        
        # Execute the pipeline
        # Since both process1 and process2 modify the text to uppercase,
        # it doesn't matter which one is executed last
        result = pipeline.execute({
            "input1": {"text": "hello"}
        })
        
        assert result == "HELLO"
    
    def test_execute_async(self, setup_registry, valid_pipeline_def, monkeypatch):
        """Test executing a pipeline asynchronously."""
        # Mock the execute method to track calls
        calls = []
        original_execute = Pipeline.execute
        
        def mock_execute(self, input_values):
            calls.append(input_values)
            return original_execute(self, input_values)
        
        monkeypatch.setattr(Pipeline, "execute", mock_execute)
        
        pipeline = Pipeline(valid_pipeline_def)
        
        # Execute asynchronously
        input_values = {"input1": {"text": "hello"}}
        pipeline.execute_async(input_values)
        
        # Wait for the thread to complete
        time.sleep(0.1)
        
        # Check that execute was called with the right arguments
        assert len(calls) == 1
        assert calls[0] == input_values