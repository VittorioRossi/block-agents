"""Tests for the BlockRegistry class."""

import pytest

from block_agents.core.block import Block
from block_agents.core.errors import BlockDefinitionError
from block_agents.core.registry import BlockRegistry, register_block


# Define some mock block classes for testing
class MockBlock1(Block):
    """Mock block for testing."""
    def process(self, inputs, context):
        return "mock1_result"


class MockBlock2(Block):
    """Another mock block for testing."""
    def process(self, inputs, context):
        return "mock2_result"


class TestBlockRegistry:
    """Tests for the BlockRegistry class."""
    
    def setup_method(self):
        """Set up the test environment."""
        # Clear the registry before each test
        BlockRegistry.clear()
    
    def test_register_and_get(self):
        """Test registering and retrieving block classes."""
        # Register a block class
        BlockRegistry.register("mock_block", MockBlock1)
        
        # Retrieve the block class
        block_class = BlockRegistry.get("mock_block")
        assert block_class == MockBlock1
    
    def test_register_decorator(self):
        """Test the register_block decorator."""
        # Define a block class with the decorator
        @register_block("decorated_block")
        class DecoratedBlock(Block):
            def process(self, inputs, context):
                return "decorated_result"
        
        # Verify that the block class was registered
        block_class = BlockRegistry.get("decorated_block")
        assert block_class == DecoratedBlock
    
    def test_get_nonexistent(self):
        """Test retrieving a non-existent block type."""
        # Attempt to retrieve a non-existent block type
        with pytest.raises(BlockDefinitionError) as excinfo:
            BlockRegistry.get("nonexistent_block")
        
        assert "Block type not registered: nonexistent_block" in str(excinfo.value)
    
    def test_get_all(self):
        """Test retrieving all registered block types."""
        # Register multiple block classes
        BlockRegistry.register("mock_block1", MockBlock1)
        BlockRegistry.register("mock_block2", MockBlock2)
        
        # Get all registered block types
        registry = BlockRegistry.get_all()
        assert registry == {
            "mock_block1": MockBlock1,
            "mock_block2": MockBlock2,
        }
        
        # Verify that the returned dictionary is a copy
        registry["new_block"] = MockBlock1
        assert "new_block" not in BlockRegistry.get_all()
    
    def test_clear(self):
        """Test clearing the registry."""
        # Register a block class
        BlockRegistry.register("mock_block", MockBlock1)
        assert "mock_block" in BlockRegistry.get_all()
        
        # Clear the registry
        BlockRegistry.clear()
        assert BlockRegistry.get_all() == {}
        
        # Verify that the block class can no longer be retrieved
        with pytest.raises(BlockDefinitionError):
            BlockRegistry.get("mock_block")
    
    def test_import_block_type(self, monkeypatch):
        """Test the dynamic import of block types."""
        # Mock the importlib.import_module function
        def mock_import_module(module_name):
            # Register the block type when the module is imported
            if module_name == "block_agents.blocks.test":
                BlockRegistry.register("test_block", MockBlock1)
            elif module_name == "block_agents.blocks.invalid":
                raise ImportError("Module not found")
        
        monkeypatch.setattr("importlib.import_module", mock_import_module)
        
        # Test successful import
        block_class = BlockRegistry.get("test_block")
        assert block_class == MockBlock1
        
        # Test failed import
        with pytest.raises(BlockDefinitionError):
            BlockRegistry.get("invalid_block")
    
    def test_register_multiple(self):
        """Test registering multiple block classes for the same type."""
        # Register a block class
        BlockRegistry.register("duplicate_block", MockBlock1)
        
        # Register another block class with the same type
        BlockRegistry.register("duplicate_block", MockBlock2)
        
        # Verify that the later registration overwrites the earlier one
        block_class = BlockRegistry.get("duplicate_block")
        assert block_class == MockBlock2