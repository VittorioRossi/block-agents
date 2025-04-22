"""Block registry for the block-based agentic pipeline system."""

import importlib
from typing import Dict, Type

from block_agents.core.errors import BlockDefinitionError


class BlockRegistry:
    """Registry for block types in the system.

    This class manages registration and retrieval of block classes by their type.
    """

    # Dictionary mapping block types to their implementing classes
    _registry: Dict[str, Type] = {}

    @classmethod
    def register(cls, block_type: str, block_class: Type) -> None:
        """Register a block class for a specific block type.

        Args:
            block_type: The block type identifier (e.g., "text_input", "llm")
            block_class: The block class implementing this type
        """
        cls._registry[block_type] = block_class

    @classmethod
    def get(cls, block_type: str) -> Type:
        """Get the block class for a specific block type.

        Args:
            block_type: The block type identifier

        Returns:
            The block class for the given type

        Raises:
            BlockDefinitionError: If the block type is not registered
        """
        if block_type not in cls._registry:
            # Try to dynamically import the block type
            if cls._import_block_type(block_type):
                return cls._registry[block_type]
            
            raise BlockDefinitionError(f"Block type not registered: {block_type}.\nAvailable block types: {', '.join(cls._registry.keys())}")
        
        return cls._registry[block_type]

    @classmethod
    def get_all(cls) -> Dict[str, Type]:
        """Get all registered block types.

        Returns:
            Dictionary mapping block types to their implementing classes
        """
        return cls._registry.copy()

    @classmethod
    def _import_block_type(cls, block_type: str) -> bool:
        """Try to import a block type.

        This method attempts to import the module that might contain the specified block type.
        For example, for block_type "text_input", it would try to import "block_agents.blocks.text".

        Args:
            block_type: The block type identifier

        Returns:
            True if the import was successful and the block type is now registered, False otherwise
        """
        # Convert block_type to potential module name
        # For example, "text_input" -> "text", "llm" -> "llm"
        module_name = block_type.split("_")[0]
        
        try:
            # Try to import the module
            importlib.import_module(f"block_agents.blocks.{module_name}")
            
            # Check if the block type is now registered
            return block_type in cls._registry
        except ImportError:
            return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered block types.

        This is primarily used for testing.
        """
        cls._registry.clear()


def register_block(block_type: str):
    """Decorator to register a block class for a specific block type.

    Args:
        block_type: The block type identifier

    Returns:
        Decorator function
    """
    def decorator(block_class: Type) -> Type:
        BlockRegistry.register(block_type, block_class)
        return block_class
    return decorator