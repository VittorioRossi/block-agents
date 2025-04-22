"""Tests for Repeater blocks."""

from typing import Any, Dict, List

import pytest

from block_agents.blocks.repeater import BatchProcessorBlock, RepeaterBlock
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError


class TestRepeaterBlock:
    """Tests for the RepeaterBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = RepeaterBlock("test_block", {
            "items_key": "test_items",
            "item_key": "test_item",
            "index_key": "test_index",
            "max_concurrent": 2,
            "collect_results": True,
            "result_key": "test_results",
            "stop_on_error": False
        })
        assert block.id == "test_block"
        assert block.items_key == "test_items"
        assert block.item_key == "test_item"
        assert block.index_key == "test_index"
        assert block.max_concurrent == 2
        assert block.collect_results is True
        assert block.result_key == "test_results"
        assert block.stop_on_error is False
        
    def test_process_items(self, mocker):
        """Test processing a list of items."""
        # Create test items
        items = ["item1", "item2", "item3"]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = RepeaterBlock("test_block", {})
        
        # Process the items
        result = block.process({"items": items}, mock_context)
        
        # Check the result
        assert "processed_count" in result
        assert result["processed_count"] == 3
        assert "total_count" in result
        assert result["total_count"] == 3
        assert "error_count" in result
        assert result["error_count"] == 0
        assert "errors" in result
        assert len(result["errors"]) == 0
        assert "results" in result
        assert len(result["results"]) == 3
        
        # Verify each result has the expected structure
        for i, item_result in enumerate(result["results"]):
            assert "item" in item_result
            assert item_result["item"] == items[i]
            assert "index" in item_result
            assert item_result["index"] == i
            assert "total" in item_result
            assert item_result["total"] == 3
            
        # Verify progress reporting and logging
        assert mock_context.log.call_count >= 3  # At least one log per item
        
    def test_process_custom_keys(self, mocker):
        """Test processing with custom item and index keys."""
        # Create test items
        items = [{"name": "Test1"}, {"name": "Test2"}]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with custom keys
        block = RepeaterBlock("test_block", {
            "items_key": "data_items",
            "item_key": "data_item",
            "index_key": "position",
            "result_key": "processed_items"
        })
        
        # Process the items
        result = block.process({"data_items": items}, mock_context)
        
        # Check the result
        assert "processed_count" in result
        assert result["processed_count"] == 2
        assert "processed_items" in result
        
        # Verify each result has the expected structure with custom keys
        for i, item_result in enumerate(result["processed_items"]):
            assert "data_item" in item_result
            assert item_result["data_item"] == items[i]
            assert "position" in item_result
            assert item_result["position"] == i
            
        # Verify logging
        mock_context.log.assert_called()
        
    def test_process_without_collecting_results(self, mocker):
        """Test processing without collecting results."""
        # Create test items
        items = ["item1", "item2", "item3"]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with collect_results=False
        block = RepeaterBlock("test_block", {
            "collect_results": False
        })
        
        # Process the items
        result = block.process({"items": items}, mock_context)
        
        # Check the result
        assert "processed_count" in result
        assert result["processed_count"] == 3
        assert "results" not in result
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_inputs_missing_items(self, mocker):
        """Test validation with missing items."""
        # Create the block
        block = RepeaterBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_invalid_items(self, mocker):
        """Test validation with invalid items (not a list)."""
        # Create the block
        block = RepeaterBlock("test_block", {})
        
        # Validate with non-list items
        with pytest.raises(InputValidationError):
            block.validate_inputs({"items": "not a list"})
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = RepeaterBlock("test_block", {})
        assert "items" in block.get_required_inputs()
        
        # With custom items key
        block2 = RepeaterBlock("test_block", {"items_key": "data_items"})
        assert "data_items" in block2.get_required_inputs()
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = RepeaterBlock("test_block", {})
        assert block.get_optional_inputs() == set()


class TestBatchProcessorBlock:
    """Tests for the BatchProcessorBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = BatchProcessorBlock("test_block", {
            "items_key": "test_items",
            "batch_size": 5,
            "batch_key": "test_batch",
            "batch_index_key": "test_batch_index",
            "collect_results": True,
            "result_key": "test_results",
            "stop_on_error": False
        })
        assert block.id == "test_block"
        assert block.items_key == "test_items"
        assert block.batch_size == 5
        assert block.batch_key == "test_batch"
        assert block.batch_index_key == "test_batch_index"
        assert block.collect_results is True
        assert block.result_key == "test_results"
        assert block.stop_on_error is False
        
    def test_process_batches(self, mocker):
        """Test processing items in batches."""
        # Create test items
        items = [f"item{i}" for i in range(20)]  # 20 items
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with batch size of 5
        block = BatchProcessorBlock("test_block", {
            "batch_size": 5
        })
        
        # Process the items
        result = block.process({"items": items}, mock_context)
        
        # Check the result
        assert "processed_batches" in result
        assert result["processed_batches"] == 4  # 20 items in batches of 5 = 4 batches
        assert "total_batches" in result
        assert result["total_batches"] == 4
        assert "total_items" in result
        assert result["total_items"] == 20
        assert "batch_size" in result
        assert result["batch_size"] == 5
        assert "error_count" in result
        assert result["error_count"] == 0
        assert "errors" in result
        assert len(result["errors"]) == 0
        assert "results" in result
        assert len(result["results"]) == 4  # 4 batches
        
        # Verify each batch result has the expected structure
        for i, batch_result in enumerate(result["results"]):
            assert "batch" in batch_result
            assert isinstance(batch_result["batch"], list)
            assert len(batch_result["batch"]) == 5
            assert "batch_index" in batch_result
            assert batch_result["batch_index"] == i
            assert "total_batches" in batch_result
            assert batch_result["total_batches"] == 4
            assert "batch_size" in batch_result
            assert batch_result["batch_size"] == 5
            
        # Verify progress reporting and logging
        assert mock_context.log.call_count >= 4  # At least one log per batch
        
    def test_process_uneven_batches(self, mocker):
        """Test processing items where last batch is smaller."""
        # Create test items
        items = [f"item{i}" for i in range(17)]  # 17 items
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with batch size of 5
        block = BatchProcessorBlock("test_block", {
            "batch_size": 5
        })
        
        # Process the items
        result = block.process({"items": items}, mock_context)
        
        # Check the result
        assert "processed_batches" in result
        assert result["processed_batches"] == 4  # 17 items in batches of 5 = 4 batches (last one with 2 items)
        assert "total_batches" in result
        assert result["total_batches"] == 4
        assert "total_items" in result
        assert result["total_items"] == 17
        
        # Verify batch sizes
        assert len(result["results"][0]["batch"]) == 5
        assert len(result["results"][1]["batch"]) == 5
        assert len(result["results"][2]["batch"]) == 5
        assert len(result["results"][3]["batch"]) == 2  # Last batch has only 2 items
        
        # Verify the batch_size metadata is correct
        assert result["results"][0]["batch_size"] == 5
        assert result["results"][1]["batch_size"] == 5
        assert result["results"][2]["batch_size"] == 5
        assert result["results"][3]["batch_size"] == 2
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_process_with_custom_batch_size(self, mocker):
        """Test processing with custom batch size passed in inputs."""
        # Create test items
        items = [f"item{i}" for i in range(10)]  # 10 items
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with default batch size
        block = BatchProcessorBlock("test_block", {
            "batch_size": 5
        })
        
        # Process the items with custom batch size
        result = block.process({
            "items": items,
            "batch_size": 2
        }, mock_context)
        
        # Check the result
        assert "processed_batches" in result
        assert result["processed_batches"] == 5  # 10 items in batches of 2 = 5 batches
        assert "total_batches" in result
        assert result["total_batches"] == 5
        assert "batch_size" in result
        assert result["batch_size"] == 2  # Custom batch size
        
        # Verify each batch has 2 items
        for batch_result in result["results"]:
            assert len(batch_result["batch"]) == 2
            
        # Verify logging
        mock_context.log.assert_called()
        
    def test_process_custom_keys(self, mocker):
        """Test processing with custom item and batch keys."""
        # Create test items
        items = [{"name": f"Test{i}"} for i in range(6)]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with custom keys
        block = BatchProcessorBlock("test_block", {
            "items_key": "data_items",
            "batch_key": "data_batch",
            "batch_index_key": "batch_position",
            "batch_size": 3,
            "result_key": "processed_batches"
        })
        
        # Process the items
        result = block.process({"data_items": items}, mock_context)
        
        # Check the result
        assert "processed_batches" in result
        assert len(result["processed_batches"]) == 2  # The result should be a list of 2 batch results
        assert "processed_batches" in result
        
        # Verify each result has the expected structure with custom keys
        for i, batch_result in enumerate(result["processed_batches"]):
            assert "data_batch" in batch_result
            assert isinstance(batch_result["data_batch"], list)
            assert len(batch_result["data_batch"]) == 3
            assert "batch_position" in batch_result
            assert batch_result["batch_position"] == i
            
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_inputs_missing_items(self, mocker):
        """Test validation with missing items."""
        # Create the block
        block = BatchProcessorBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_invalid_items(self, mocker):
        """Test validation with invalid items (not a list)."""
        # Create the block
        block = BatchProcessorBlock("test_block", {})
        
        # Validate with non-list items
        with pytest.raises(InputValidationError):
            block.validate_inputs({"items": "not a list"})
            
    def test_validate_inputs_invalid_batch_size(self, mocker):
        """Test validation with invalid batch size."""
        # Create the block
        block = BatchProcessorBlock("test_block", {})
        
        # Validate with invalid batch size
        with pytest.raises(InputValidationError):
            block.validate_inputs({
                "items": ["item1", "item2"],
                "batch_size": -5
            })
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = BatchProcessorBlock("test_block", {})
        assert "items" in block.get_required_inputs()
        
        # With custom items key
        block2 = BatchProcessorBlock("test_block", {"items_key": "data_items"})
        assert "data_items" in block2.get_required_inputs()
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = BatchProcessorBlock("test_block", {})
        assert "batch_size" in block.get_optional_inputs()