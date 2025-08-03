"""Tests for file handling blocks."""

import json
import os
import tempfile
from typing import Any, Dict

import pytest
import yaml

from block_agents.blocks.file import FileWriterBlock, InputFileBlock
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError


class TestInputFileBlock:
    """Tests for the InputFileBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = InputFileBlock("test_block", {"file_path": "test.txt"})
        assert block.id == "test_block"
        assert block.file_path == "test.txt"
        assert block.file_format == "auto"
        assert block.encoding == "utf-8"
        
    def test_detect_format(self):
        """Test format detection from file extension."""
        block = InputFileBlock("test_block", {})
        assert block._detect_format("test.json") == "json"
        assert block._detect_format("test.csv") == "csv"
        assert block._detect_format("test.yaml") == "yaml"
        assert block._detect_format("test.yml") == "yaml"
        assert block._detect_format("test.txt") == "text"
        assert block._detect_format("test") == "text"
        
    def test_read_text_file(self, mocker):
        """Test reading a text file."""
        # Create a test text file
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("Hello, world!")
            temp_path = f.name
            
        try:
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = InputFileBlock("test_block", {})
            
            # Process the file
            result = block.process({"file_path": temp_path}, mock_context)
            
            # Check the result
            assert "text" in result
            assert result["text"] == "Hello, world!"
            
            # Verify logging
            mock_context.log.assert_called()
        finally:
            # Clean up
            os.remove(temp_path)
            
    def test_read_json_file(self, mocker):
        """Test reading a JSON file."""
        # Create a test JSON file
        test_data = {"name": "Test", "value": 123}
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as f:
            json.dump(test_data, f)
            temp_path = f.name
            
        try:
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = InputFileBlock("test_block", {})
            
            # Process the file
            result = block.process({"file_path": temp_path}, mock_context)
            
            # Check the result
            assert "data" in result
            assert result["data"] == test_data
            
            # Verify logging
            mock_context.log.assert_called()
        finally:
            # Clean up
            os.remove(temp_path)
            
    def test_read_csv_file(self, mocker):
        """Test reading a CSV file."""
        # Create a test CSV file
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".csv") as f:
            f.write("name,value\nTest,123\nTest2,456")
            temp_path = f.name
            
        try:
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = InputFileBlock("test_block", {})
            
            # Process the file
            result = block.process({"file_path": temp_path}, mock_context)
            
            # Check the result
            assert "data" in result
            assert len(result["data"]) == 2
            assert result["data"][0]["name"] == "Test"
            assert result["data"][0]["value"] == "123"
            assert result["data"][1]["name"] == "Test2"
            assert result["data"][1]["value"] == "456"
            
            # Verify logging
            mock_context.log.assert_called()
        finally:
            # Clean up
            os.remove(temp_path)
            
    def test_read_yaml_file(self, mocker):
        """Test reading a YAML file."""
        # Create a test YAML file
        test_data = {"name": "Test", "value": 123, "nested": {"key": "value"}}
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as f:
            yaml.dump(test_data, f)
            temp_path = f.name
            
        try:
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = InputFileBlock("test_block", {})
            
            # Process the file
            result = block.process({"file_path": temp_path}, mock_context)
            
            # Check the result
            assert "data" in result
            assert result["data"] == test_data
            
            # Verify logging
            mock_context.log.assert_called()
        finally:
            # Clean up
            os.remove(temp_path)
            
    def test_validate_inputs_missing_file(self, mocker):
        """Test validation with missing file path."""
        # Create the block
        block = InputFileBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_nonexistent_file(self, mocker):
        """Test validation with nonexistent file."""
        # Create the block
        block = InputFileBlock("test_block", {})
        
        # Validate with nonexistent file
        with pytest.raises(InputValidationError):
            block.validate_inputs({"file_path": "/nonexistent/file.txt"})
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        # With file path in config
        block1 = InputFileBlock("test_block", {"file_path": "test.txt"})
        assert block1.get_required_inputs() == set()
        
        # Without file path in config
        block2 = InputFileBlock("test_block", {})
        assert block2.get_required_inputs() == {"file_path"}
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        # With file path in config
        block1 = InputFileBlock("test_block", {"file_path": "test.txt"})
        assert block1.get_optional_inputs() == {"file_path"}
        
        # Without file path in config
        block2 = InputFileBlock("test_block", {})
        assert block2.get_optional_inputs() == set()


class TestFileWriterBlock:
    """Tests for the FileWriterBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = FileWriterBlock("test_block", {"file_path": "test.txt"})
        assert block.id == "test_block"
        assert block.file_path == "test.txt"
        assert block.file_format == "auto"
        assert block.encoding == "utf-8"
        assert block.overwrite is True
        
    def test_detect_format(self):
        """Test format detection from file extension."""
        block = FileWriterBlock("test_block", {})
        assert block._detect_format("test.json") == "json"
        assert block._detect_format("test.csv") == "csv"
        assert block._detect_format("test.yaml") == "yaml"
        assert block._detect_format("test.yml") == "yaml"
        assert block._detect_format("test.txt") == "text"
        assert block._detect_format("test") == "text"
        
    def test_write_text_file(self, mocker):
        """Test writing a text file."""
        # Create a temporary directory for the test file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file path in the temp directory
            file_path = os.path.join(temp_dir, "test.txt")
            
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = FileWriterBlock("test_block", {})
            
            # Process the write operation
            result = block.process({
                "file_path": file_path,
                "text": "Hello, world!"
            }, mock_context)
            
            # Check the result
            assert "file_path" in result
            assert result["file_path"] == file_path
            
            # Verify the file was written
            assert os.path.exists(file_path)
            with open(file_path) as f:
                content = f.read()
                assert content == "Hello, world!"
                
            # Verify logging
            mock_context.log.assert_called()
            
    def test_write_json_file(self, mocker):
        """Test writing a JSON file."""
        # Create a temporary directory for the test file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file path in the temp directory
            file_path = os.path.join(temp_dir, "test.json")
            
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = FileWriterBlock("test_block", {"json_options": {"indent": 4}})
            
            # Data to write
            test_data = {"name": "Test", "value": 123}
            
            # Process the write operation
            result = block.process({
                "file_path": file_path,
                "data": test_data
            }, mock_context)
            
            # Check the result
            assert "file_path" in result
            assert result["file_path"] == file_path
            
            # Verify the file was written
            assert os.path.exists(file_path)
            with open(file_path) as f:
                loaded_data = json.load(f)
                assert loaded_data == test_data
                
            # Verify logging
            mock_context.log.assert_called()
            
    def test_write_csv_file(self, mocker):
        """Test writing a CSV file."""
        # Create a temporary directory for the test file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file path in the temp directory
            file_path = os.path.join(temp_dir, "test.csv")
            
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = FileWriterBlock("test_block", {})
            
            # Data to write
            test_data = [
                {"name": "Test1", "value": 123},
                {"name": "Test2", "value": 456}
            ]
            
            # Process the write operation
            result = block.process({
                "file_path": file_path,
                "data": test_data
            }, mock_context)
            
            # Check the result
            assert "file_path" in result
            assert result["file_path"] == file_path
            
            # Verify the file was written
            assert os.path.exists(file_path)
            
            # Read back and check content
            with open(file_path) as f:
                content = f.read()
                assert "name,value" in content
                assert "Test1,123" in content
                assert "Test2,456" in content
                
            # Verify logging
            mock_context.log.assert_called()
            
    def test_write_yaml_file(self, mocker):
        """Test writing a YAML file."""
        # Create a temporary directory for the test file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file path in the temp directory
            file_path = os.path.join(temp_dir, "test.yaml")
            
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = FileWriterBlock("test_block", {})
            
            # Data to write
            test_data = {
                "name": "Test", 
                "value": 123,
                "nested": {"key": "value"}
            }
            
            # Process the write operation
            result = block.process({
                "file_path": file_path,
                "data": test_data
            }, mock_context)
            
            # Check the result
            assert "file_path" in result
            assert result["file_path"] == file_path
            
            # Verify the file was written
            assert os.path.exists(file_path)
            
            # Read back and check content
            with open(file_path) as f:
                loaded_data = yaml.safe_load(f)
                assert loaded_data == test_data
                
            # Verify logging
            mock_context.log.assert_called()
            
    def test_validate_inputs_missing_file(self, mocker):
        """Test validation with missing file path."""
        # Create the block
        block = FileWriterBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_missing_data(self, mocker):
        """Test validation with missing data."""
        # Create the block
        block = FileWriterBlock("test_block", {})
        
        # Validate with missing data
        with pytest.raises(InputValidationError):
            block.validate_inputs({"file_path": "test.txt"})
            
    def test_no_overwrite(self, mocker):
        """Test not overwriting existing files."""
        # Create a temporary directory for the test file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file path in the temp directory
            file_path = os.path.join(temp_dir, "test.txt")
            
            # Create the file first
            with open(file_path, "w") as f:
                f.write("Original content")
                
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block with overwrite=False
            block = FileWriterBlock("test_block", {"overwrite": False})
            
            # Process the write operation
            result = block.process({
                "file_path": file_path,
                "text": "New content"
            }, mock_context)
            
            # Check the result
            assert "file_path" in result
            assert result["file_path"] == file_path
            
            # Verify the file was not overwritten
            with open(file_path) as f:
                content = f.read()
                assert content == "Original content"
                
            # Verify logging
            mock_context.log.assert_called()
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        # With file path in config
        block1 = FileWriterBlock("test_block", {"file_path": "test.txt"})
        assert block1.get_required_inputs() == set()
        
        # Without file path in config
        block2 = FileWriterBlock("test_block", {})
        assert block2.get_required_inputs() == {"file_path"}
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        # With file path in config
        block1 = FileWriterBlock("test_block", {"file_path": "test.txt"})
        assert "file_path" in block1.get_optional_inputs()
        assert "text" in block1.get_optional_inputs()
        assert "data" in block1.get_optional_inputs()
        
        # Without file path in config
        block2 = FileWriterBlock("test_block", {})
        assert "text" in block2.get_optional_inputs()
        assert "data" in block2.get_optional_inputs()