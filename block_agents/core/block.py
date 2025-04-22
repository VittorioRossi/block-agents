"""Base Block class for the block-based agentic pipeline system."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union

from block_agents.core.context import Context
from block_agents.core.errors import BlockTimeoutError


class Block(ABC):
    """Abstract base class for all blocks in the system.

    Blocks are the fundamental units of computation in the pipeline system. Each
    block takes inputs, performs some processing, and produces outputs.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new Block.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        self.id = block_id
        self.config = config
        
        # Default timeout in seconds (can be overridden in config)
        self.timeout = config.get("timeout_seconds", 60)

    def execute(self, inputs: Dict[str, Any], context: Context) -> Any:
        """Execute the block with the given inputs and context.

        This method handles the execution lifecycle:
        1. Validate inputs
        2. Emit start event
        3. Process inputs
        4. Validate outputs
        5. Emit complete event

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Block output

        Raises:
            InputValidationError: If input validation fails
            OutputValidationError: If output validation fails
            BlockRuntimeError: If there's a runtime error
            TimeoutError: If execution times out
        """
        stream = context.get_stream_manager()
        
        # Check timeout
        timeout = self.config.get("timeout_seconds", self.timeout)
        
        # Emit start event
        stream.emit_start(self.id, self.config)
        
        try:
            # Validate inputs
            self.validate_inputs(inputs)
            
            # Time execution
            start_time = time.time()
            
            # Process inputs
            result = self.process(inputs, context)
            
            # Check if execution exceeded timeout
            execution_time = time.time() - start_time
            if timeout and execution_time > timeout:
                raise BlockTimeoutError(
                    f"Block execution exceeded timeout of {timeout} seconds",
                    block_id=self.id,
                    details={"execution_time": execution_time, "timeout": timeout},
                )
            
            # Validate outputs
            self.validate_output(result)
            
            # Emit complete event
            stream.emit_complete(self.id, result)
            
            return result
            
        except Exception as e:
            # Emit error event
            stream.emit_error(self.id, e)
            
            # Re-raise the exception
            raise

    @abstractmethod
    def process(self, inputs: Dict[str, Any], context: Context) -> Any:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Block output
        """
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Default implementation does nothing
        pass

    def validate_output(self, output: Any) -> None:
        """Validate the output of the block.

        Args:
            output: Block output

        Raises:
            OutputValidationError: If validation fails
        """
        # Default implementation does nothing
        pass

    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        return set()

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return set()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration for this block.

        Returns:
            Default configuration dictionary
        """
        return {
            "timeout_seconds": 60,
        }
    
    def get_description(self) -> str:
        """Get a description of this block.

        Returns:
            Block description
        """
        return self.__doc__ or "No description available"
    
    def report_progress(self, context: Context, progress: float, partial_result: Optional[Any] = None) -> None:
        """Report progress to the stream manager.

        Args:
            context: Execution context
            progress: Progress value between 0 and 1
            partial_result: Partial result if available
        """
        if 0 <= progress <= 1:
            stream = context.get_stream_manager()
            stream.emit_progress(self.id, progress, partial_result)
        
    def log(self, context: Context, message: str, level: str = "info") -> None:
        """Log a message to the stream.

        Args:
            context: Execution context
            message: The message
            level: Log level (debug, info, warning, error)
        """
        stream = context.get_stream_manager()
        stream.emit_log(self.id, message, level)


class BlockFactory:
    """Factory for creating block instances."""
    
    @staticmethod
    def create_block(block_type: str, block_id: str, config: Dict[str, Any]) -> Block:
        """Create a block instance.

        Args:
            block_type: The block type identifier
            block_id: Unique identifier for the block instance
            config: Block configuration

        Returns:
            A new Block instance

        Raises:
            BlockDefinitionError: If the block type is not registered
        """
        from block_agents.core.registry import BlockRegistry
        
        # Get the block class from the registry
        block_class = BlockRegistry.get(block_type)
        
        # Create an instance
        return block_class(block_id, config)