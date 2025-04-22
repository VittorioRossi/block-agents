"""Tests for JSON Schema blocks."""

import json
import tempfile
from typing import Any, Dict

import pytest

from block_agents.blocks.json_schema import JSONTransformerBlock, JSONValidatorBlock
from block_agents.core.context import Context
from block_agents.core.errors import BlockRuntimeError, InputValidationError


class TestJSONValidatorBlock:
    """Tests for the JSONValidatorBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        block = JSONValidatorBlock("test_block", {"schema": schema})
        assert block.id == "test_block"
        assert block.schema == schema
        assert block.schema_file == ""
        assert block.fail_on_invalid is True
        
    def test_validate_valid_data(self, mocker):
        """Test validating valid data."""
        # Create a schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name"]
        }
        
        # Create valid data
        data = {"name": "John", "age": 30}
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = JSONValidatorBlock("test_block", {"schema": schema})
        
        # Process the validation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "valid" in result
        assert result["valid"] is True
        assert "errors" in result
        assert len(result["errors"]) == 0
        assert "data" in result
        assert result["data"] == data
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_invalid_data(self, mocker):
        """Test validating invalid data."""
        # Create a schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name", "age"]
        }
        
        # Create invalid data (missing required field)
        data = {"name": "John"}
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with fail_on_invalid=False
        block = JSONValidatorBlock("test_block", {
            "schema": schema,
            "fail_on_invalid": False
        })
        
        # Process the validation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "valid" in result
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "data" in result
        assert result["data"] == data
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_invalid_data_with_failure(self, mocker):
        """Test validating invalid data with failure enabled."""
        # Create a schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name", "age"]
        }
        
        # Create invalid data (missing required field)
        data = {"name": "John"}
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with fail_on_invalid=True
        block = JSONValidatorBlock("test_block", {
            "schema": schema,
            "fail_on_invalid": True
        })
        
        # Process the validation with expected error
        with pytest.raises(BlockRuntimeError) as exc_info:
            block.process({"data": data}, mock_context)
            
        # Verify the error message
        assert "validation failed" in str(exc_info.value)
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_with_schema_from_input(self, mocker):
        """Test validating with schema from input."""
        # Create a schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        
        # Create valid data
        data = {"name": "John"}
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block without schema in config
        block = JSONValidatorBlock("test_block", {})
        
        # Process the validation
        result = block.process({
            "data": data,
            "schema": schema
        }, mock_context)
        
        # Check the result
        assert "valid" in result
        assert result["valid"] is True
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_inputs_missing_data(self, mocker):
        """Test validation with missing data."""
        # Create the block
        block = JSONValidatorBlock("test_block", {
            "schema": {"type": "object"}
        })
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_missing_schema(self, mocker):
        """Test validation with missing schema."""
        # Create the block without schema
        block = JSONValidatorBlock("test_block", {})
        
        # Validate with missing schema
        with pytest.raises(InputValidationError):
            block.validate_inputs({"data": {}})
            
    def test_validate_inputs_invalid_schema(self, mocker):
        """Test validation with invalid schema."""
        # Create the block without schema
        block = JSONValidatorBlock("test_block", {})
        
        # Validate with invalid schema
        with pytest.raises(InputValidationError):
            block.validate_inputs({
                "data": {},
                "schema": {"invalid": "schema"}  # Not a valid JSON Schema
            })
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = JSONValidatorBlock("test_block", {})
        assert "data" in block.get_required_inputs()
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = JSONValidatorBlock("test_block", {})
        assert "schema" in block.get_optional_inputs()


class TestJSONTransformerBlock:
    """Tests for the JSONTransformerBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = JSONTransformerBlock("test_block", {
            "select": ["name", "age"],
            "rename": {"name": "full_name"},
            "transform": {"age": "string"},
            "flatten": True
        })
        assert block.id == "test_block"
        assert block.select == ["name", "age"]
        assert block.rename == {"name": "full_name"}
        assert block.transform == {"age": "string"}
        assert block.flatten is True
        
    def test_transform_object_select(self, mocker):
        """Test transforming an object with select."""
        # Create input data
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "address": "123 Main St"
        }
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with select
        block = JSONTransformerBlock("test_block", {
            "select": ["name", "age"]
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert "name" in result["data"]
        assert "age" in result["data"]
        assert "email" not in result["data"]
        assert "address" not in result["data"]
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_object_rename(self, mocker):
        """Test transforming an object with rename."""
        # Create input data
        data = {
            "name": "John",
            "age": 30
        }
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with rename
        block = JSONTransformerBlock("test_block", {
            "rename": {"name": "full_name", "age": "years"}
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert "full_name" in result["data"]
        assert "years" in result["data"]
        assert "name" not in result["data"]
        assert "age" not in result["data"]
        assert result["data"]["full_name"] == "John"
        assert result["data"]["years"] == 30
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_object_transform(self, mocker):
        """Test transforming an object with transform."""
        # Create input data
        data = {
            "name": "john",
            "age": "30",
            "active": 1
        }
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with transform
        block = JSONTransformerBlock("test_block", {
            "transform": {
                "name": "uppercase",
                "age": "integer",
                "active": "boolean"
            }
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert result["data"]["name"] == "JOHN"
        assert result["data"]["age"] == 30
        assert result["data"]["active"] is True
        assert isinstance(result["data"]["age"], int)
        assert isinstance(result["data"]["active"], bool)
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_object_flatten(self, mocker):
        """Test transforming an object with flatten."""
        # Create input data
        data = {
            "name": "John",
            "contact": {
                "email": "john@example.com",
                "phone": "123-456-7890"
            }
        }
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with flatten
        block = JSONTransformerBlock("test_block", {
            "flatten": True
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert "name" in result["data"]
        assert "contact_email" in result["data"]
        assert "contact_phone" in result["data"]
        assert "contact" not in result["data"]
        assert result["data"]["contact_email"] == "john@example.com"
        assert result["data"]["contact_phone"] == "123-456-7890"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_array_filter(self, mocker):
        """Test transforming an array with filter."""
        # Create input data
        data = [
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": False},
            {"name": "Bob", "age": 40, "active": True}
        ]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with filter
        block = JSONTransformerBlock("test_block", {
            "filter": {"active": True}
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "John"
        assert result["data"][1]["name"] == "Bob"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_array_complex_filter(self, mocker):
        """Test transforming an array with complex filter."""
        # Create input data
        data = [
            {"name": "John", "age": 30, "dept": "IT"},
            {"name": "Jane", "age": 25, "dept": "HR"},
            {"name": "Bob", "age": 40, "dept": "IT"},
            {"name": "Alice", "age": 35, "dept": "Finance"}
        ]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with complex filter
        block = JSONTransformerBlock("test_block", {
            "filter": {
                "age": {"gt": 25},
                "dept": {"neq": "HR"}
            }
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert len(result["data"]) == 3
        assert result["data"][0]["name"] == "John"
        assert result["data"][1]["name"] == "Bob"
        assert result["data"][2]["name"] == "Alice"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_array_with_string_operations(self, mocker):
        """Test transforming an array with string operations."""
        # Create input data
        data = [
            {"name": "John Smith", "email": "john@example.com"},
            {"name": "Jane Doe", "email": "jane@example.com"}
        ]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with string filters
        block = JSONTransformerBlock("test_block", {
            "filter": {
                "name": {"contains": "John"},
                "email": {"endswith": "example.com"}
            }
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "John Smith"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_transform_combined(self, mocker):
        """Test transforming with multiple operations combined."""
        # Create input data
        data = [
            {"name": "john smith", "age": "30", "contact": {"email": "john@example.com"}},
            {"name": "jane doe", "age": "25", "contact": {"email": "jane@example.com"}},
            {"name": "bob jones", "age": "40", "contact": {"email": "bob@example.com"}}
        ]
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with combined operations
        block = JSONTransformerBlock("test_block", {
            "select": ["name", "age", "contact"],
            "rename": {"name": "full_name"},
            "transform": {"full_name": "uppercase", "age": "integer"},
            "flatten": True,
            "filter": {"age": {"gte": 30}}
        })
        
        # Process the transformation
        result = block.process({"data": data}, mock_context)
        
        # Check the result
        assert "data" in result
        assert len(result["data"]) == 2
        assert "full_name" in result["data"][0]
        assert "age" in result["data"][0]
        assert "contact_email" in result["data"][0]
        assert result["data"][0]["full_name"] == "JOHN SMITH"
        assert result["data"][0]["age"] == 30
        assert result["data"][1]["full_name"] == "BOB JONES"
        assert result["data"][1]["age"] == 40
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_inputs_missing_data(self, mocker):
        """Test validation with missing data."""
        # Create the block
        block = JSONTransformerBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_invalid_select(self, mocker):
        """Test validation with invalid select."""
        # Create the block
        block = JSONTransformerBlock("test_block", {})
        
        # Validate with invalid select
        with pytest.raises(InputValidationError):
            block.validate_inputs({
                "data": {},
                "select": "not a list"
            })
            
    def test_validate_inputs_invalid_rename(self, mocker):
        """Test validation with invalid rename."""
        # Create the block
        block = JSONTransformerBlock("test_block", {})
        
        # Validate with invalid rename
        with pytest.raises(InputValidationError):
            block.validate_inputs({
                "data": {},
                "rename": "not a dict"
            })
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = JSONTransformerBlock("test_block", {})
        assert "data" in block.get_required_inputs()
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = JSONTransformerBlock("test_block", {})
        assert "select" in block.get_optional_inputs()
        assert "rename" in block.get_optional_inputs()
        assert "transform" in block.get_optional_inputs()
        assert "flatten" in block.get_optional_inputs()
        assert "filter" in block.get_optional_inputs()