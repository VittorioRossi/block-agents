
"""Pipeline execution engine for the block-based agentic pipeline system."""

import hashlib
import json
import os
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from block_agents.core.block import Block, BlockFactory
from block_agents.core.client_manager import LLMClientManager
from block_agents.core.config import Config
from block_agents.core.context import Context
from block_agents.core.errors import (
    BlockRuntimeError,
    PipelineDefinitionError,
    PipelineRuntimeError,
)
from block_agents.core.stream import StreamEvent, StreamManager


class Pipeline:
    """Pipeline execution engine.

    This class is responsible for:
    - Validating pipeline definitions
    - Creating and managing blocks
    - Orchestrating block execution
    - Streaming execution events
    """

    def __init__(
        self,
        pipeline_def: Dict[str, Any],
        config: Optional[Config] = None,
    ):
        """Initialize a new Pipeline.

        Args:
            pipeline_def: Pipeline definition
            config: Configuration instance (if not provided, a default one will be loaded)

        Raises:
            PipelineDefinitionError: If the pipeline definition is invalid
        """
        # Load config if not provided
        self.config = config or Config.load()
        
        # Validate pipeline definition
        self._validate_pipeline_def(pipeline_def)
        
        # Store pipeline definition
        self.pipeline_def = pipeline_def
        
        # Extract pipeline metadata
        self.pipeline_id = pipeline_def.get("pipeline_id", str(uuid.uuid4()))
        self.name = pipeline_def.get("name", f"Pipeline {self.pipeline_id}")
        self.description = pipeline_def.get("description", "")
        
        # Get stream configuration
        stream_config = pipeline_def.get("stream_config", {})
        
        # Create stream manager
        self.stream_manager = StreamManager(
            pipeline_id=self.pipeline_id,
            enabled=stream_config.get("enabled", True),
            log_level=stream_config.get("log_level", self.config.get("log_level", "info")),
            include_block_types=stream_config.get("include_block_types", []),
            throttle_ms=stream_config.get("throttle_ms", 100),
        )
        
        # Create execution context
        self.context = Context(
            pipeline_id=self.pipeline_id,
            config=self.config,
            stream_manager=self.stream_manager,
        )
        
        # Create LLM client manager
        self.client_manager = LLMClientManager(self.config)
        self.context.set_client_manager(self.client_manager)
        
        # Create blocks
        self.blocks: Dict[str, Block] = {}
        for block_def in pipeline_def.get("blocks", []):
            block_id = block_def.get("id")
            block_type = block_def.get("type")
            block_config = block_def.get("config", {})
            
            try:
                block = BlockFactory.create_block(block_type, block_id, block_config)
                self.blocks[block_id] = block
            except Exception as e:
                raise PipelineDefinitionError(
                    f"Error creating block {block_id} of type {block_type}: {e}",
                    block_id=block_id,
                ) from e
                
        # Build block dependency graph
        self.block_dependencies: Dict[str, List[str]] = {}
        self.next_blocks: Dict[str, List[str]] = {}
        
        for block_def in pipeline_def.get("blocks", []):
            block_id = block_def.get("id")
            next_blocks = block_def.get("next", [])
            
            self.next_blocks[block_id] = next_blocks
            
            for next_block_id in next_blocks:
                if next_block_id not in self.block_dependencies:
                    self.block_dependencies[next_block_id] = []
                self.block_dependencies[next_block_id].append(block_id)
                
        # Identify entry point blocks (blocks with no dependencies)
        self.entry_blocks = [
            block_id for block_id in self.blocks
            if block_id not in self.block_dependencies or not self.block_dependencies[block_id]
        ]
        
        # Validate that there is at least one entry point
        if not self.entry_blocks:
            raise PipelineDefinitionError("Pipeline has no entry points")
            
        # Identify output block
        self.output_block_id = pipeline_def.get("output")
        if self.output_block_id and self.output_block_id not in self.blocks:
            raise PipelineDefinitionError(f"Output block not found: {self.output_block_id}")
            
        # Subscribers for events
        self.subscribers: List[Callable[[StreamEvent], None]] = []

    def _validate_pipeline_def(self, pipeline_def: Dict[str, Any]) -> None:
        """Validate a pipeline definition.

        Args:
            pipeline_def: Pipeline definition to validate

        Raises:
            PipelineDefinitionError: If the pipeline definition is invalid
        """
        # Check required fields
        if not isinstance(pipeline_def, dict):
            raise PipelineDefinitionError("Pipeline definition must be a dictionary")
            
        if "blocks" not in pipeline_def:
            raise PipelineDefinitionError("Pipeline definition must contain 'blocks'")
            
        if not isinstance(pipeline_def["blocks"], list):
            raise PipelineDefinitionError("'blocks' must be a list")
            
        # Check that blocks have unique IDs
        block_ids = set()
        for i, block_def in enumerate(pipeline_def["blocks"]):
            if not isinstance(block_def, dict):
                raise PipelineDefinitionError(f"Block at index {i} must be a dictionary")
                
            if "id" not in block_def:
                raise PipelineDefinitionError(f"Block at index {i} must have an 'id'")
                
            if "type" not in block_def:
                raise PipelineDefinitionError(f"Block at index {i} must have a 'type'")
                
            block_id = block_def["id"]
            if block_id in block_ids:
                raise PipelineDefinitionError(f"Duplicate block ID: {block_id}")
                
            block_ids.add(block_id)
            
            # Check that 'next' refers to valid blocks
            next_blocks = block_def.get("next", [])
            if not isinstance(next_blocks, list):
                raise PipelineDefinitionError(f"'next' for block {block_id} must be a list")
                
        # Check that all 'next' references refer to valid blocks
        for block_def in pipeline_def["blocks"]:
            block_id = block_def["id"]
            next_blocks = block_def.get("next", [])
            
            for next_block_id in next_blocks:
                if next_block_id not in block_ids:
                    raise PipelineDefinitionError(
                        f"Block {block_id} references non-existent block: {next_block_id}"
                    )
                    
        # Check for circular dependencies
        for block_id in block_ids:
            visited = set()
            if self._check_circular_dependency(block_id, visited, pipeline_def):
                raise PipelineDefinitionError(f"Circular dependency detected starting from block {block_id}")

    def _check_circular_dependency(
        self, block_id: str, visited: Set[str], pipeline_def: Dict[str, Any]
    ) -> bool:
        """Check for circular dependencies in the pipeline.

        Args:
            block_id: Current block ID
            visited: Set of visited block IDs
            pipeline_def: Pipeline definition

        Returns:
            True if a circular dependency is detected, False otherwise
        """
        if block_id in visited:
            return True
            
        visited.add(block_id)
        
        # Find the block definition
        block_def = None
        for b in pipeline_def["blocks"]:
            if b["id"] == block_id:
                block_def = b
                break
                
        if not block_def:
            return False
            
        # Check each next block
        for next_block_id in block_def.get("next", []):
            if self._check_circular_dependency(next_block_id, visited.copy(), pipeline_def):
                return True
                
        return False

    def add_subscriber(self, subscriber: Callable[[StreamEvent], None]) -> None:
        """Add a subscriber to receive stream events.

        Args:
            subscriber: Callback function to receive events
        """
        self.stream_manager.add_subscriber(subscriber)
        self.subscribers.append(subscriber)

    def remove_subscriber(self, subscriber: Callable[[StreamEvent], None]) -> None:
        """Remove a subscriber.

        Args:
            subscriber: Callback function to remove
        """
        self.stream_manager.remove_subscriber(subscriber)
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)

    def execute(self, input_values: Dict[str, Any]) -> Any:
        """Execute the pipeline with the given input values.

        Args:
            input_values: Input values for the pipeline

        Returns:
            Pipeline output

        Raises:
            PipelineRuntimeError: If there's a runtime error
        """
        # Set up global values
        global_values = input_values.get("global_parameters", {})
        for key, value in global_values.items():
            self.context.set_global_value(key, value)
            
        # Emit pipeline start event
        self.stream_manager.emit(
            event_type="pipeline_start",
            block_id="pipeline",
            data={
                "pipeline_id": self.pipeline_id,
                "name": self.name,
                "description": self.description,
            },
        )
        
        try:
            # Start execution timer
            start_time = time.time()
            max_runtime = self.context.get_max_runtime_seconds()
            
            # Execute blocks
            executed_blocks = set()
            pending_blocks = set(self.blocks.keys())
            
            # Process all entry blocks first
            for block_id in self.entry_blocks:
                block_input = input_values.get(block_id, {})
                self._execute_block(block_id, block_input, executed_blocks, pending_blocks)
                
            # Process remaining blocks if needed
            while pending_blocks:
                next_block = self._find_next_executable_block(executed_blocks, pending_blocks)
                if not next_block:
                    # Can't make any more progress
                    break
                    
                # Check execution time
                elapsed_time = time.time() - start_time
                if max_runtime and elapsed_time > max_runtime:
                    raise PipelineRuntimeError(
                        f"Pipeline execution exceeded maximum runtime of {max_runtime} seconds",
                        details={"elapsed_time": elapsed_time, "max_runtime": max_runtime},
                    )
                    
                # Get block input from dependencies
                block_input = self._get_block_input(next_block)
                
                # Execute the block
                self._execute_block(next_block, block_input, executed_blocks, pending_blocks)
                
            # Check if output block was executed
            if self.output_block_id and self.output_block_id in executed_blocks:
                output = self.context.get_block_value(self.output_block_id)
            else:
                # Return all block outputs
                output = self.context.get_all_block_values()
                
            # Emit pipeline completion event
            self.stream_manager.emit(
                event_type="pipeline_complete",
                block_id="pipeline",
                data={
                    "pipeline_id": self.pipeline_id,
                    "execution_time": time.time() - start_time,
                    "executed_blocks": list(executed_blocks),
                    "pending_blocks": list(pending_blocks),
                },
            )
            
            return output
            
        except Exception as e:
            # Emit pipeline error event
            self.stream_manager.emit_error("pipeline", e)
            
            # Re-raise as PipelineRuntimeError
            if not isinstance(e, PipelineRuntimeError):
                raise PipelineRuntimeError(
                    f"Pipeline execution error: {e}",
                    details={"error_type": e.__class__.__name__},
                ) from e
            raise

    def _execute_block(
        self,
        block_id: str,
        block_input: Dict[str, Any],
        executed_blocks: Set[str],
        pending_blocks: Set[str],
    ) -> Any:
        """Execute a block and update execution state.

        Args:
            block_id: ID of the block to execute
            block_input: Input values for the block
            executed_blocks: Set of executed block IDs (will be updated)
            pending_blocks: Set of pending block IDs (will be updated)

        Returns:
            Block output

        Raises:
            BlockRuntimeError: If there's a runtime error
        """
        if block_id not in self.blocks:
            raise BlockRuntimeError(f"Block not found: {block_id}")
            
        block = self.blocks[block_id]
        
        try:
            # Execute the block
            output = block.execute(block_input, self.context)
            
            # Store the output in the context
            self.context.set_block_value(block_id, output)
            
            # Update execution state
            executed_blocks.add(block_id)
            pending_blocks.discard(block_id)
            
            return output
            
        except Exception as e:
            # Update execution state
            executed_blocks.add(block_id)
            pending_blocks.discard(block_id)
            
            # Re-raise as BlockRuntimeError
            if not isinstance(e, BlockRuntimeError):
                raise BlockRuntimeError(
                    f"Error executing block {block_id}: {e}",
                    block_id=block_id,
                    details={"error_type": e.__class__.__name__},
                ) from e 
            raise

    def _find_next_executable_block(
        self, executed_blocks: Set[str], pending_blocks: Set[str]
    ) -> Optional[str]:
        """Find the next block that can be executed.

        A block can be executed if all its dependencies have been executed.

        Args:
            executed_blocks: Set of executed block IDs
            pending_blocks: Set of pending block IDs

        Returns:
            ID of the next executable block, or None if no block can be executed
        """
        for block_id in pending_blocks:
            if block_id not in self.block_dependencies:
                # No dependencies, can be executed
                return block_id
                
            # Check if all dependencies have been executed
            dependencies = self.block_dependencies[block_id]
            if all(dep in executed_blocks for dep in dependencies):
                return block_id
                
        return None

    def _get_block_input(self, block_id: str) -> Dict[str, Any]:
        """Get input values for a block from its dependencies.

        Args:
            block_id: ID of the block

        Returns:
            Input values for the block
        """
        input_values = {}
        
        if block_id in self.block_dependencies:
            for dep_id in self.block_dependencies[block_id]:
                # Get the output of the dependency
                dep_output = self.context.get_block_value(dep_id)
                
                # Add to input values
                if isinstance(dep_output, dict):
                    # If dependency output is a dict, merge it
                    for key, value in dep_output.items():
                        input_values[key] = value
                else:
                    # Otherwise, use the dependency ID as the key
                    input_values[dep_id] = dep_output
                    
        # Add global values
        for key, value in self.context.get_all_global_values().items():
            # Don't overwrite existing values
            if key not in input_values:
                input_values[key] = value
                
        return input_values

    def execute_async(self, input_values: Dict[str, Any]) -> None:
        """Execute the pipeline asynchronously.

        Args:
            input_values: Input values for the pipeline
        """
        thread = threading.Thread(target=self.execute, args=(input_values,))
        thread.daemon = True
        thread.start()

    @classmethod
    def from_json(cls, json_str: str, config: Optional[Config] = None) -> "Pipeline":
        """Create a Pipeline from a JSON string.

        Args:
            json_str: JSON string containing the pipeline definition
            config: Configuration instance

        Returns:
            A new Pipeline instance

        Raises:
            PipelineDefinitionError: If the pipeline definition is invalid
        """
        try:
            pipeline_def = json.loads(json_str)
            return cls(pipeline_def, config)
        except json.JSONDecodeError as e:
            raise PipelineDefinitionError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise PipelineDefinitionError(f"Error creating pipeline: {e}") from e

    @classmethod
    def from_frontend_json(cls, json_str: str, config: Optional[Config] = None) -> "Pipeline":
        """Create a Pipeline from a frontend workflow JSON string.

        Args:
            json_str: JSON string containing the frontend workflow definition
            config: Configuration instance

        Returns:
            A new Pipeline instance

        Raises:
            PipelineDefinitionError: If the frontend workflow definition is invalid
        """
        from block_agents.parsers import FrontendParser
        
        try:
            frontend_data = json.loads(json_str)
            pipeline_def = FrontendParser.parse(frontend_data)
            return cls(pipeline_def, config)
        except json.JSONDecodeError as e:
            raise PipelineDefinitionError(f"Invalid JSON: {e}") from e 
        except Exception as e:
            raise PipelineDefinitionError(f"Error creating pipeline from frontend data: {e}") from e

    @classmethod
    def from_frontend_dict(cls, frontend_data: Dict[str, Any], config: Optional[Config] = None) -> "Pipeline":
        """Create a Pipeline from a frontend workflow dictionary.

        Args:
            frontend_data: Dictionary containing the frontend workflow definition
            config: Configuration instance

        Returns:
            A new Pipeline instance

        Raises:
            PipelineDefinitionError: If the frontend workflow definition is invalid
        """
        from block_agents.parsers import FrontendParser
        
        try:
            pipeline_def = FrontendParser.parse(frontend_data)
            return cls(pipeline_def, config)
        except Exception as e:
            raise PipelineDefinitionError(f"Error creating pipeline from frontend data: {e}") from e 

    def to_json(self) -> str:
        """Convert the pipeline definition to a JSON string.

        Returns:
            JSON string containing the pipeline definition
        """
        return json.dumps(self.pipeline_def)