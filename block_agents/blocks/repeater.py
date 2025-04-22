"""Repeater block for the block-based agentic pipeline system."""

from typing import Any, Dict, List, Optional, Set, Tuple

from block_agents.core.block import Block
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError
from block_agents.core.registry import register_block


@register_block("repeater")
class RepeaterBlock(Block):
    """Block for repeating operations over collections of data.
    
    This block allows users to iterate over a list of items and apply the same
    pipeline operations to each item in the list, collecting the results.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new RepeaterBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get repeater options from config
        self.items_key = config.get("items_key", "items")
        self.item_key = config.get("item_key", "item")
        self.index_key = config.get("index_key", "index")
        self.max_concurrent = config.get("max_concurrent", 1)
        self.collect_results = config.get("collect_results", True)
        self.result_key = config.get("result_key", "results")
        self.stop_on_error = config.get("stop_on_error", True)
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the processing results
        """
        # Get items to iterate over
        items = inputs.get(self.items_key, [])
        
        # Check if items is a list
        if not isinstance(items, list):
            raise InputValidationError(
                f"Input '{self.items_key}' must be a list",
                block_id=self.id,
                details={"input_type": type(items).__name__},
            )
            
        # Log operation
        total_items = len(items)
        context.log(self.id, f"Starting iteration over {total_items} items")
        
        # Initialize result collection
        results = []
        errors = []
        
        # Iterate over items
        for idx, item in enumerate(items):
            # Report progress
            progress = idx / total_items if total_items > 0 else 0
            self.report_progress(context, progress)
            
            # Create item context
            item_context = {
                self.item_key: item,
                self.index_key: idx,
                "total": total_items
            }
            
            # Log current item
            context.log(self.id, f"Processing item {idx+1}/{total_items}")
            
            try:
                # Process this item using the next blocks in the pipeline
                # Note: The actual processing is not done here since this is a control block
                # The pipeline executor will handle directing the flow to the next blocks
                
                # For this block, we just pass along the item context to the next blocks
                item_result = item_context
                
                # Add to results if collecting
                if self.collect_results:
                    results.append(item_result)
                    
            except Exception as e:
                context.log(self.id, f"Error processing item {idx+1}: {str(e)}", level="error")
                errors.append({
                    "index": idx,
                    "item": item,
                    "error": str(e)
                })
                
                # Stop if configured to do so
                if self.stop_on_error:
                    context.log(self.id, "Stopping iteration due to error", level="error")
                    break
        
        # Report completion
        self.report_progress(context, 1.0)
        
        # Create result
        result = {
            "processed_count": len(items) - len(errors),
            "total_count": len(items),
            "error_count": len(errors),
            "errors": errors
        }
        
        # Add collected results if configured
        if self.collect_results:
            result[self.result_key] = results
            
        # Log completion
        context.log(self.id, f"Completed iteration over {len(items)} items with {len(errors)} errors")
        
        return result
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Items are required
        if self.items_key not in inputs:
            raise InputValidationError(
                f"Required input '{self.items_key}' not found",
                block_id=self.id,
            )
            
        # Items must be a list
        items = inputs.get(self.items_key)
        if not isinstance(items, list):
            raise InputValidationError(
                f"Input '{self.items_key}' must be a list",
                block_id=self.id,
                details={"input_type": type(items).__name__},
            )
            
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        return {self.items_key}

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return set()


@register_block("batch_processor")
class BatchProcessorBlock(Block):
    """Block for processing data in batches.
    
    This block is a specialized version of the repeater that processes data in batches
    rather than individual items, which can be more efficient for certain operations.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new BatchProcessorBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get batch options from config
        self.items_key = config.get("items_key", "items")
        self.batch_size = config.get("batch_size", 10)
        self.batch_key = config.get("batch_key", "batch")
        self.batch_index_key = config.get("batch_index_key", "batch_index")
        self.collect_results = config.get("collect_results", True)
        self.result_key = config.get("result_key", "results")
        self.stop_on_error = config.get("stop_on_error", True)
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the processing results
        """
        # Get items to batch
        items = inputs.get(self.items_key, [])
        batch_size = inputs.get("batch_size", self.batch_size)
        
        # Check if items is a list
        if not isinstance(items, list):
            raise InputValidationError(
                f"Input '{self.items_key}' must be a list",
                block_id=self.id,
                details={"input_type": type(items).__name__},
            )
            
        # Create batches
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
            
        # Log operation
        total_batches = len(batches)
        context.log(self.id, f"Starting batch processing with {total_batches} batches (batch size {batch_size})")
        
        # Initialize result collection
        results = []
        errors = []
        
        # Process batches
        for batch_idx, batch in enumerate(batches):
            # Report progress
            progress = batch_idx / total_batches if total_batches > 0 else 0
            self.report_progress(context, progress)
            
            # Create batch context
            batch_context = {
                self.batch_key: batch,
                self.batch_index_key: batch_idx,
                "total_batches": total_batches,
                "batch_size": len(batch)
            }
            
            # Log current batch
            context.log(self.id, f"Processing batch {batch_idx+1}/{total_batches} with {len(batch)} items")
            
            try:
                # Process this batch using the next blocks in the pipeline
                # Note: The actual processing is not done here since this is a control block
                # The pipeline executor will handle directing the flow to the next blocks
                
                # For this block, we just pass along the batch context to the next blocks
                batch_result = batch_context
                
                # Add to results if collecting
                if self.collect_results:
                    results.append(batch_result)
                    
            except Exception as e:
                context.log(self.id, f"Error processing batch {batch_idx+1}: {str(e)}", level="error")
                errors.append({
                    "batch_index": batch_idx,
                    "batch": batch,
                    "error": str(e)
                })
                
                # Stop if configured to do so
                if self.stop_on_error:
                    context.log(self.id, "Stopping batch processing due to error", level="error")
                    break
        
        # Report completion
        self.report_progress(context, 1.0)
        
        # Create result
        result = {
            "processed_batches": len(batches) - len(errors),
            "total_batches": len(batches),
            "total_items": len(items),
            "batch_size": batch_size,
            "error_count": len(errors),
            "errors": errors
        }
        
        # Add collected results if configured
        if self.collect_results:
            result[self.result_key] = results
            
        # Log completion
        context.log(self.id, f"Completed batch processing of {len(items)} items in {len(batches)} batches with {len(errors)} errors")
        
        return result
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Items are required
        if self.items_key not in inputs:
            raise InputValidationError(
                f"Required input '{self.items_key}' not found",
                block_id=self.id,
            )
            
        # Items must be a list
        items = inputs.get(self.items_key)
        if not isinstance(items, list):
            raise InputValidationError(
                f"Input '{self.items_key}' must be a list",
                block_id=self.id,
                details={"input_type": type(items).__name__},
            )
            
        # Validate batch_size if provided
        if "batch_size" in inputs:
            batch_size = inputs["batch_size"]
            if not isinstance(batch_size, int) or batch_size <= 0:
                raise InputValidationError(
                    "Input 'batch_size' must be a positive integer",
                    block_id=self.id,
                    details={"input_value": batch_size},
                )
            
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        return {self.items_key}

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return {"batch_size"}