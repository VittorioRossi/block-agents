"""Tests for text-related blocks."""

import pytest

from block_agents.blocks.text import TextFormatterBlock, TextInputBlock, TextJoinerBlock
from block_agents.core.config import Config
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError


@pytest.fixture
def context():
    """Create a mock context for testing."""
    config = Config({
        "log_level": "info",
    })
    return Context(
        pipeline_id="test-pipeline",
        config=config
    )


class TestTextInputBlock:
    """Tests for the TextInputBlock class."""
    
    def test_init(self):
        """Test TextInputBlock initialization."""
        # Test with default config
        block = TextInputBlock("test_block", {})
        assert block.id == "test_block"
        assert block.default_text == ""
        assert block.format_options == {}
        
        # Test with custom config
        block = TextInputBlock("test_block", {
            "default_text": "Default text",
            "format_options": {"uppercase": True}
        })
        assert block.default_text == "Default text"
        assert block.format_options == {"uppercase": True}
    
    def test_process(self, context):
        """Test processing inputs."""
        block = TextInputBlock("test_block", {
            "default_text": "Default text"
        })
        
        # Test with provided text
        result = block.process({"text": "Hello world"}, context)
        assert result == {"text": "Hello world"}
        
        # Test with default text
        result = block.process({}, context)
        assert result == {"text": "Default text"}
    
    def test_validate_inputs(self):
        """Test input validation."""
        block = TextInputBlock("test_block", {})
        
        # Valid input
        block.validate_inputs({"text": "Hello world"})
        
        # Empty input (should use default)
        block.validate_inputs({})
        
        # Invalid input type
        with pytest.raises(InputValidationError) as excinfo:
            block.validate_inputs({"text": 123})
        assert "Input 'text' must be a string" in str(excinfo.value)
    
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = TextInputBlock("test_block", {})
        assert block.get_required_inputs() == set()
    
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = TextInputBlock("test_block", {})
        assert block.get_optional_inputs() == {"text"}


class TestTextFormatterBlock:
    """Tests for the TextFormatterBlock class."""
    
    def test_init(self):
        """Test TextFormatterBlock initialization."""
        # Test with default config
        block = TextFormatterBlock("test_block", {})
        assert block.id == "test_block"
        assert block.case is None
        assert block.trim is False
        assert block.prefix == ""
        assert block.suffix == ""
        assert block.replace == {}
        
        # Test with custom config
        block = TextFormatterBlock("test_block", {
            "case": "upper",
            "trim": True,
            "prefix": "Start: ",
            "suffix": " :End",
            "replace": {"hello": "hi"}
        })
        assert block.case == "upper"
        assert block.trim is True
        assert block.prefix == "Start: "
        assert block.suffix == " :End"
        assert block.replace == {"hello": "hi"}
    
    def test_process_case(self, context):
        """Test text case formatting."""
        # Test uppercase
        block = TextFormatterBlock("test_block", {"case": "upper"})
        result = block.process({"text": "Hello world"}, context)
        assert result == {"text": "HELLO WORLD"}
        
        # Test lowercase
        block = TextFormatterBlock("test_block", {"case": "lower"})
        result = block.process({"text": "Hello World"}, context)
        assert result == {"text": "hello world"}
        
        # Test title case
        block = TextFormatterBlock("test_block", {"case": "title"})
        result = block.process({"text": "hello world"}, context)
        assert result == {"text": "Hello World"}
        
        # Test sentence case
        block = TextFormatterBlock("test_block", {"case": "sentence"})
        result = block.process({"text": "hello world"}, context)
        assert result == {"text": "Hello world"}
    
    def test_process_trim(self, context):
        """Test trimming whitespace."""
        block = TextFormatterBlock("test_block", {"trim": True})
        result = block.process({"text": "  Hello world  "}, context)
        assert result == {"text": "Hello world"}
    
    def test_process_prefix_suffix(self, context):
        """Test adding prefix and suffix."""
        block = TextFormatterBlock("test_block", {
            "prefix": "Start: ",
            "suffix": " :End"
        })
        result = block.process({"text": "Hello world"}, context)
        assert result == {"text": "Start: Hello world :End"}
    
    def test_process_replace(self, context):
        """Test replacing text."""
        block = TextFormatterBlock("test_block", {
            "replace": {"Hello": "Hi", "world": "there"}
        })
        result = block.process({"text": "Hello world"}, context)
        assert result == {"text": "Hi there"}
    
    def test_validate_inputs(self):
        """Test input validation."""
        block = TextFormatterBlock("test_block", {})
        
        # Valid input
        block.validate_inputs({"text": "Hello world"})
        
        # Missing required input
        with pytest.raises(InputValidationError) as excinfo:
            block.validate_inputs({})
        assert "Required input 'text' not found" in str(excinfo.value)
        
        # Invalid input type
        with pytest.raises(InputValidationError) as excinfo:
            block.validate_inputs({"text": 123})
        assert "Input 'text' must be a string" in str(excinfo.value)
    
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        block = TextFormatterBlock("test_block", {})
        assert block.get_required_inputs() == {"text"}
    
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = TextFormatterBlock("test_block", {})
        assert block.get_optional_inputs() == set()


class TestTextJoinerBlock:
    """Tests for the TextJoinerBlock class."""
    
    def test_init(self):
        """Test TextJoinerBlock initialization."""
        # Test with default config
        block = TextJoinerBlock("test_block", {})
        assert block.id == "test_block"
        assert block.separator == "\n"
        assert block.prefix == ""
        assert block.suffix == ""
        assert block.input_keys == []
        
        # Test with custom config
        block = TextJoinerBlock("test_block", {
            "separator": ", ",
            "prefix": "Start: ",
            "suffix": " :End",
            "input_keys": ["text1", "text2"]
        })
        assert block.separator == ", "
        assert block.prefix == "Start: "
        assert block.suffix == " :End"
        assert block.input_keys == ["text1", "text2"]
    
    def test_process_with_input_keys(self, context):
        """Test joining text with specified input keys."""
        block = TextJoinerBlock("test_block", {
            "separator": ", ",
            "input_keys": ["text1", "text2"]
        })
        result = block.process({
            "text1": "Hello",
            "text2": "world",
            "text3": "ignored"
        }, context)
        assert result == {"text": "Hello, world"}
    
    def test_process_without_input_keys(self, context):
        """Test joining all string inputs."""
        block = TextJoinerBlock("test_block", {
            "separator": ", "
        })
        result = block.process({
            "text1": "Hello",
            "text2": "world",
            "number": 123  # Should be ignored
        }, context)
        assert result == {"text": "Hello, world"}
    
    def test_process_with_prefix_suffix(self, context):
        """Test joining with prefix and suffix."""
        block = TextJoinerBlock("test_block", {
            "separator": ", ",
            "prefix": "Start: ",
            "suffix": " :End"
        })
        result = block.process({
            "text1": "Hello",
            "text2": "world"
        }, context)
        assert result == {"text": "Start: Hello, world :End"}
    
    def test_validate_inputs_with_input_keys(self):
        """Test input validation with specified input keys."""
        block = TextJoinerBlock("test_block", {
            "input_keys": ["text1", "text2"]
        })
        
        # Valid input
        block.validate_inputs({
            "text1": "Hello",
            "text2": "world"
        })
        
        # Valid with only one of the specified keys
        block.validate_inputs({
            "text1": "Hello"
        })
        
        # Invalid with none of the specified keys
        with pytest.raises(InputValidationError) as excinfo:
            block.validate_inputs({
                "text3": "Hello"
            })
        assert "None of the specified input keys" in str(excinfo.value)
    
    def test_validate_inputs_without_input_keys(self):
        """Test input validation without specified input keys."""
        block = TextJoinerBlock("test_block", {})
        
        # Valid input
        block.validate_inputs({
            "text1": "Hello",
            "text2": "world"
        })
        
        # Invalid with no string inputs
        with pytest.raises(InputValidationError) as excinfo:
            block.validate_inputs({
                "number": 123
            })
        assert "No string inputs found" in str(excinfo.value)
    
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        # With input keys
        block = TextJoinerBlock("test_block", {
            "input_keys": ["text1", "text2"]
        })
        assert block.get_required_inputs() == {"text1", "text2"}
        
        # Without input keys
        block = TextJoinerBlock("test_block", {})
        assert block.get_required_inputs() == set()
    
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        block = TextJoinerBlock("test_block", {})
        assert block.get_optional_inputs() == set()