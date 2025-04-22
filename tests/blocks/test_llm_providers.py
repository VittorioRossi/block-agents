"""Tests for LLM provider implementations."""

import json
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types.message import ContentBlock
from anthropic.types.message import Message as AnthropicMessage
from anthropic.types.message import Usage as MessageUsage

from block_agents.blocks.llm_providers.anthropic import AnthropicClient
from block_agents.blocks.llm_providers.ollama import OllamaClient
from block_agents.blocks.llm_providers.openai import OpenAIClient
from block_agents.core.config import Config
from block_agents.core.errors import LLMProviderError


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config_dict = {
        "llm": {
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "default_model": "gpt-4",
                    "timeout_seconds": 60,
                },
                "anthropic": {
                    "default_model": "claude-3-opus-20240229",
                    "timeout_seconds": 120,
                },
                "ollama": {
                    "default_model": "llama2",
                    "endpoint": "http://localhost:11434",
                    "timeout_seconds": 60,
                },
            },
        },
    }
    return Config(config_dict)


class TestOpenAIClient:
    """Tests for the OpenAIClient."""
    
    @patch("openai.OpenAI")
    def test_init(self, mock_openai_client, mock_config):
        """Test client initialization."""
        # Setup mock config to return API key
        mock_config.get_api_key = MagicMock(return_value="test-api-key")
        
        # Create client
        client = OpenAIClient(mock_config)
        
        # Check initialization
        assert client.provider == "openai"
        assert client.default_model == "gpt-4"
        assert client.timeout_seconds == 60
        assert client.api_key == "test-api-key"
        
        # Check that OpenAI client was created
        mock_openai_client.assert_called_once_with(api_key="test-api-key")
    
    @patch("openai.OpenAI")
    def test_generate(self, mock_openai_client, mock_config):
        """Test text generation."""
        # Setup mock config to return API key
        mock_config.get_api_key = MagicMock(return_value="test-api-key")
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client
        
        # Create client
        client = OpenAIClient(mock_config)
        
        # Generate text
        response = client.generate(
            prompt="Test prompt",
            temperature=0.5,
            max_tokens=100,
            system_message="System message",
        )
        
        # Check response
        assert response.text == "Generated text"
        assert response.model == "gpt-4"
        assert response.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        assert response.raw_response == mock_response
        
        # Check that client was called
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "System message"},
                {"role": "user", "content": "Test prompt"},
            ],
            max_tokens=100,
            temperature=0.5,
            timeout=60,
        )
        
    @patch("openai.OpenAI")
    def test_stream_generate(self, mock_openai_client, mock_config):
        """Test streaming text generation."""
        # Setup mock config to return API key
        mock_config.get_api_key = MagicMock(return_value="test-api-key")
        
        # Setup mock response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Generated "
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "text"
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]
        mock_openai_client.return_value = mock_client
        
        # Create client
        client = OpenAIClient(mock_config)
        
        # Track callback calls
        callback_calls = []
        def callback(text):
            callback_calls.append(text)
        
        # Stream generate text
        response = client.stream_generate(
            prompt="Test prompt",
            callback=callback,
            temperature=0.5,
            max_tokens=100,
            system_message="System message",
        )
        
        # Check response
        assert response.text == "Generated text"
        assert response.model == "gpt-4"
        assert response.usage["completion_tokens"] == 2
        assert callback_calls == ["Generated ", "text"]
        
        # Check that client was called
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "System message"},
                {"role": "user", "content": "Test prompt"},
            ],
            max_tokens=100,
            temperature=0.5,
            timeout=60,
            stream=True,
        )


class TestAnthropicClient:
    """Tests for the AnthropicClient."""
    
    @patch("anthropic.Anthropic")
    def test_init(self, mock_anthropic_client, mock_config):
        """Test client initialization."""
        # Setup mock config to return API key
        mock_config.get_api_key = MagicMock(return_value="test-api-key")
        
        # Create client
        client = AnthropicClient(mock_config)
        
        # Check initialization
        assert client.provider == "anthropic"
        assert client.default_model == "claude-3-opus-20240229"
        assert client.timeout_seconds == 120
        assert client.api_key == "test-api-key"
        
        # Check that Anthropic client was created
        mock_anthropic_client.assert_called_once_with(api_key="test-api-key")
    
    @patch("anthropic.Anthropic")
    def test_generate(self, mock_anthropic_client, mock_config):
        """Test text generation."""
        # Setup mock config to return API key
        mock_config.get_api_key = MagicMock(return_value="test-api-key")
        
        # Setup mock response using MagicMock instead of direct instantiation
        mock_response = MagicMock()
        # Content is a list of content blocks
        mock_content = MagicMock()
        mock_content.text = "Generated text"
        mock_content.type = "text"
        mock_response.content = [mock_content]  
        mock_response.id = "msg_123"
        mock_response.model = "claude-3-opus-20240229"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_client.return_value = mock_client
        
        # Create client
        client = AnthropicClient(mock_config)
        
        # Generate text
        response = client.generate(
            prompt="Test prompt",
            temperature=0.5,
            max_tokens=100,
            system_message="System message",
        )
        
        # Check response
        assert response.text == "Generated text"
        assert response.model == "claude-3-opus-20240229"
        assert response.usage == {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }
        assert response.raw_response == mock_response
        
        # Check that client was called
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-opus-20240229",
            messages=[
                {"role": "user", "content": "Test prompt"}
            ],
            system="System message",
            max_tokens=100,
            temperature=0.5,
        )
        
    @patch("anthropic.Anthropic")
    def test_stream_generate(self, mock_anthropic_client, mock_config):
        """Test streaming text generation."""
        # Setup mock config to return API key
        mock_config.get_api_key = MagicMock(return_value="test-api-key")
        
        # Setup mock response chunks as dictionaries
        mock_chunk1 = MagicMock()
        mock_chunk1.type = "content_block_delta"
        mock_chunk1.delta = MagicMock(text="Generated ")
        mock_chunk1.index = 0
        
        mock_chunk2 = MagicMock()
        mock_chunk2.type = "content_block_delta"
        mock_chunk2.delta = MagicMock(text="text")
        mock_chunk2.index = 0
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.messages.create.return_value = [mock_chunk1, mock_chunk2]
        mock_anthropic_client.return_value = mock_client
        
        # Create client
        client = AnthropicClient(mock_config)
        
        # Track callback calls
        callback_calls = []
        def callback(text):
            callback_calls.append(text)
        
        # Stream generate text
        response = client.stream_generate(
            prompt="Test prompt",
            callback=callback,
            temperature=0.5,
            max_tokens=100,
            system_message="System message",
        )
        
        # Check response
        assert response.text == "Generated text"
        assert response.model == "claude-3-opus-20240229"
        assert response.usage["output_tokens"] == 2
        assert callback_calls == ["Generated ", "text"]
        
        # Check that client was called
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-opus-20240229",
            messages=[
                {"role": "user", "content": "Test prompt"}
            ],
            system="System message",
            max_tokens=100,
            temperature=0.5,
            stream=True,
        )


class TestOllamaClient:
    """Tests for the OllamaClient."""
    
    def test_init(self, mock_config):
        """Test client initialization."""
        # API key is optional for Ollama, so we don't mock it
        
        # Create client
        client = OllamaClient(mock_config)
        
        # Check initialization
        assert client.provider == "ollama"
        assert client.default_model == "llama2"
        assert client.timeout_seconds == 60
        assert client.endpoint == "http://localhost:11434"
        assert client.api_key == ""  # Empty string if no API key provided
    
    @patch("requests.post")
    def test_generate(self, mock_post, mock_config):
        """Test text generation."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "model": "llama2",
            "response": "Generated text",
            "prompt_eval_count": 10,
            "eval_count": 20,
        }
        mock_post.return_value = mock_response
        
        # Create client
        client = OllamaClient(mock_config)
        
        # Generate text
        response = client.generate(
            prompt="Test prompt",
            temperature=0.5,
            max_tokens=100,
            system_message="System message",
        )
        
        # Check response
        assert response.text == "Generated text"
        assert response.model == "llama2"
        assert response.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        
        # Check that request was made
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            headers={"Content-Type": "application/json"},
            json={
                "model": "llama2",
                "prompt": "Test prompt",
                "system": "System message",
                "temperature": 0.5,
                "num_predict": 100,
            },
            timeout=60,
        )
        
    @patch("requests.post")
    def test_stream_generate(self, mock_post, mock_config):
        """Test streaming text generation."""
        # Setup mock response for streaming
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            json.dumps({
                "model": "llama2",
                "response": "Generated ",
                "prompt_eval_count": 10,
            }).encode(),
            json.dumps({
                "model": "llama2",
                "response": "text",
                "prompt_eval_count": 10,
            }).encode(),
            json.dumps({
                "model": "llama2",
                "done": True,
                "eval_count": 20,
            }).encode(),
        ]
        mock_post.return_value = mock_response
        
        # Create client
        client = OllamaClient(mock_config)
        
        # Track callback calls
        callback_calls = []
        def callback(text):
            callback_calls.append(text)
        
        # Stream generate text
        response = client.stream_generate(
            prompt="Test prompt",
            callback=callback,
            temperature=0.5,
            max_tokens=100,
            system_message="System message",
        )
        
        # Check response
        assert response.text == "Generated text"
        assert response.model == "llama2"
        assert response.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        assert callback_calls == ["Generated ", "text"]
        
        # Check that request was made
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            headers={"Content-Type": "application/json"},
            json={
                "model": "llama2",
                "prompt": "Test prompt",
                "system": "System message",
                "temperature": 0.5,
                "num_predict": 100,
                "stream": True,
            },
            stream=True,
            timeout=60,
        )
    
    @patch("requests.post")
    def test_generate_error(self, mock_post, mock_config):
        """Test error handling in generate."""
        # Setup mock to raise an exception
        mock_post.side_effect = Exception("Test error")
        
        # Create client
        client = OllamaClient(mock_config)
        
        # Generate text should raise an error
        with pytest.raises(LLMProviderError) as excinfo:
            client.generate(prompt="Test prompt")
        
        assert "Unexpected error: Test error" in str(excinfo.value)