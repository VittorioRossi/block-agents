"""Ollama provider for LLM integration."""

import json
from typing import Any, Callable, Dict, Optional

import requests

from block_agents.core.client_manager import (
    BaseLLMClient,
    LLMResponse,
    register_provider,
)
from block_agents.core.config import Config
from block_agents.core.errors import LLMProviderError


class OllamaClient(BaseLLMClient):
    """Client for Ollama LLM provider."""

    def __init__(self, config: Config, provider: str = "ollama"):
        """Initialize a new OllamaClient.

        Args:
            config: Configuration instance
            provider: Provider name
        """
        super().__init__(config, provider)
        
        # Get endpoint from config
        self.endpoint = config.get(f"llm.providers.{provider}.endpoint", "http://localhost:11434")
        
        # API key is not required for Ollama
        if not self.api_key:
            self.api_key = ""

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text from the LLM.

        Args:
            prompt: The input prompt
            model: Model to use (defaults to provider's default model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse instance

        Raises:
            LLMProviderError: If there's an error from the provider
        """
        try:
            # Use default model if not specified
            if not model:
                model = self.default_model
                
            # Prepare system message
            system_message = kwargs.get("system_message", "")
            
            # Prepare request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system_message,
                "temperature": temperature,
                "num_predict": max_tokens,
            }
            
            # Add any additional Ollama parameters
            for key, value in kwargs.items():
                if key not in ["system_message"]:
                    payload[key] = value
            
            # Send request to Ollama API
            response = requests.post(
                f"{self.endpoint}/api/generate",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_seconds,
            )
            
            # Raise error if unsuccessful
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract text
            text = response_data.get("response", "")
            
            # Get token usage if available
            usage = {
                "prompt_tokens": response_data.get("prompt_eval_count", 0),
                "completion_tokens": response_data.get("eval_count", 0),
                "total_tokens": response_data.get("prompt_eval_count", 0) + response_data.get("eval_count", 0),
            }
            
            return LLMResponse(
                text=text,
                model=model,
                usage=usage,
                raw_response=response_data,
            )
            
        except requests.RequestException as e:
            raise LLMProviderError(
                f"Ollama request error: {e}",
                details={"error_type": type(e).__name__},
            )
        except json.JSONDecodeError as e:
            raise LLMProviderError(
                f"Ollama response parsing error: {e}",
                details={"error_type": "JSONDecodeError"},
            )
        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                details={"error_type": type(e).__name__},
            )

    def stream_generate(
        self,
        prompt: str,
        callback: Callable[[str], None],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Stream text generation from the LLM.

        Args:
            prompt: The input prompt
            callback: Callback function to receive generated text
            model: Model to use (defaults to provider's default model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse instance

        Raises:
            LLMProviderError: If there's an error from the provider
        """
        try:
            # Use default model if not specified
            if not model:
                model = self.default_model
                
            # Prepare system message
            system_message = kwargs.get("system_message", "")
            
            # Prepare request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system_message,
                "temperature": temperature,
                "num_predict": max_tokens,
                "stream": True,
            }
            
            # Add any additional Ollama parameters
            for key, value in kwargs.items():
                if key not in ["system_message"]:
                    payload[key] = value
            
            # Send request to Ollama API
            response = requests.post(
                f"{self.endpoint}/api/generate",
                headers={"Content-Type": "application/json"},
                json=payload,
                stream=True,
                timeout=self.timeout_seconds,
            )
            
            # Raise error if unsuccessful
            response.raise_for_status()
            
            # Variables to collect the response
            full_text = ""
            prompt_tokens = 0
            completion_tokens = 0
            
            # Stream the response
            for line in response.iter_lines():
                if line:
                    # Parse line as JSON
                    line_data = json.loads(line)
                    
                    # Get chunk of text
                    chunk_text = line_data.get("response", "")
                    if chunk_text:
                        full_text += chunk_text
                        
                        # Call the callback with the chunk
                        callback(chunk_text)
                        
                        # Increment token count
                        completion_tokens += 1
                    
                    # Update token counts if available
                    if "prompt_eval_count" in line_data:
                        prompt_tokens = line_data["prompt_eval_count"]
                    
                    # Check if done
                    if line_data.get("done", False):
                        # Update final token counts
                        if "eval_count" in line_data:
                            completion_tokens = line_data["eval_count"]
                        break
            
            return LLMResponse(
                text=full_text,
                model=model,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                raw_response=None,  # Can't return the streaming response
            )
            
        except requests.RequestException as e:
            raise LLMProviderError(
                f"Ollama request error: {e}",
                details={"error_type": type(e).__name__},
            )
        except json.JSONDecodeError as e:
            raise LLMProviderError(
                f"Ollama response parsing error: {e}",
                details={"error_type": "JSONDecodeError"},
            )
        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                details={"error_type": type(e).__name__},
            )


# Register the provider
register_provider("ollama", OllamaClient)