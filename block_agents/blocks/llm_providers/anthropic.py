"""Anthropic provider for LLM integration."""

from typing import Callable, Optional

import anthropic

from block_agents.core.client_manager import (
    BaseLLMClient,
    LLMResponse,
    register_provider,
)
from block_agents.core.config import Config
from block_agents.core.errors import LLMProviderError


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic LLM provider."""

    def __init__(self, config: Config, provider: str = "anthropic"):
        """Initialize a new AnthropicClient.

        Args:
            config: Configuration instance
            provider: Provider name
        """
        super().__init__(config, provider)
        
        # Create Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)

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
                
            # Prepare messages
            system_message = kwargs.get("system_message", "")
            
            # Generate response
            response = self.client.messages.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system=system_message,
                max_tokens=max_tokens,
                temperature=temperature,
                **{k: v for k, v in kwargs.items() if k not in ["system_message"]},
            )
            
            # Extract text
            text = response.content[0].text
            
            # Extract usage
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            
            return LLMResponse(
                text=text,
                model=model,
                usage=usage,
                raw_response=response,
            )
            
        except anthropic.APIError as e:
            raise LLMProviderError(
                f"Anthropic error: {e}",
                details={"error_type": type(e).__name__},
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
                
            # Prepare messages
            system_message = kwargs.get("system_message", "")
                
            # Generate streaming response
            stream = self.client.messages.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system=system_message,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ["system_message"]},
            )
            
            # Variables to collect the response
            full_text = ""
            input_tokens = 0
            output_tokens = 0
            
            # Stream the response
            for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    chunk_text = chunk.delta.text
                    full_text += chunk_text
                    
                    # Call the callback with the chunk
                    callback(chunk_text)
                    
                    # Increment token count (approximate)
                    output_tokens += 1
                    
            # Approximate input tokens
            input_tokens = len(prompt) // 4  # Very rough approximation
            
            return LLMResponse(
                text=full_text,
                model=model,
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                raw_response=None,  # Can't return the streaming response
            )
            
        except anthropic.APIError as e:
            raise LLMProviderError(
                f"Anthropic error: {e}",
                details={"error_type": type(e).__name__},
            )
        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                details={"error_type": type(e).__name__},
            )


# Register the provider
register_provider("anthropic", AnthropicClient)