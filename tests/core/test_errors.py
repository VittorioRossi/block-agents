"""Tests for the error handling system."""

import pytest

from block_agents.core.errors import (
    BlockAgentError,
    BlockDefinitionError,
    BlockRuntimeError,
    ConfigurationError,
    InputValidationError,
    OutputValidationError,
    get_error_class_by_code,
)


def test_base_error():
    """Test the base BlockAgentError class."""
    error = BlockAgentError("Test error message")
    
    assert error.message == "Test error message"
    assert error.block_id is None
    assert error.details == {}
    assert str(error) == "Test error message"
    
    # Test with block_id and details
    error = BlockAgentError(
        "Error in block", 
        block_id="test_block",
        details={"key": "value"}
    )
    
    assert error.message == "Error in block"
    assert error.block_id == "test_block"
    assert error.details == {"key": "value"}


def test_error_to_dict():
    """Test the to_dict method of BlockAgentError."""
    error = BlockAgentError(
        "Test error message",
        block_id="test_block",
        details={"key": "value"}
    )
    
    error_dict = error.to_dict()
    assert error_dict["code"] == "block_agent_error"
    assert error_dict["message"] == "Test error message"
    assert error_dict["status_code"] == 500
    assert error_dict["block_id"] == "test_block"
    assert error_dict["details"] == {"key": "value"}
    
    # Test without block_id and details
    error = BlockAgentError("Simple error")
    error_dict = error.to_dict()
    assert "block_id" not in error_dict
    assert "details" not in error_dict or error_dict["details"] == {}


def test_error_subclasses():
    """Test the error subclasses."""
    # ConfigurationError
    error = ConfigurationError("Config error")
    assert error.code == "configuration_error"
    assert error.status_code == 400
    
    # BlockDefinitionError
    error = BlockDefinitionError("Block definition error")
    assert error.code == "block_definition_error"
    assert error.status_code == 400
    
    # BlockRuntimeError
    error = BlockRuntimeError("Runtime error")
    assert error.code == "block_runtime_error"
    assert error.status_code == 500
    
    # InputValidationError
    error = InputValidationError("Invalid input")
    assert error.code == "input_validation_error"
    assert error.status_code == 400
    
    # OutputValidationError
    error = OutputValidationError("Invalid output")
    assert error.code == "output_validation_error"
    assert error.status_code == 500


def test_get_error_class_by_code():
    """Test the get_error_class_by_code function."""
    ErrorClass = get_error_class_by_code("configuration_error")
    assert ErrorClass == ConfigurationError
    
    ErrorClass = get_error_class_by_code("block_definition_error")
    assert ErrorClass == BlockDefinitionError
    
    ErrorClass = get_error_class_by_code("input_validation_error")
    assert ErrorClass == InputValidationError
    
    # Test with unknown code
    with pytest.raises(ValueError):
        get_error_class_by_code("unknown_error_code")