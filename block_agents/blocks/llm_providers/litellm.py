"""LiteLLM provider for LLM integration."""

from typing import Callable, Optional

import litellm

from block_agents.core.client_manager import (
    BaseLLMClient,
    LLMResponse,
    register_provider,
)
from block_agents.core.config import Config
from block_agents.core.errors import LLMProviderError


class LiteLLMClient(BaseLLMClient):
    """Client for LiteLLM provider supporting 100+ LLM providers.
    
    LiteLLM provides a unified interface to access multiple LLM providers
    including OpenAI, Anthropic, Cohere, HuggingFace, Azure OpenAI, and many others.
    It automatically translates OpenAI-compatible parameters across all providers.
    """

    def __init__(self, config: Config, provider: str = "litellm") -> None:
        """Initialize a new LiteLLMClient.

        Args:
            config: Configuration instance
            provider: Provider name
        """
        super().__init__(config, provider)

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: object,
    ) -> LLMResponse:
        """Generate text from the LLM using LiteLLM.

        LiteLLM automatically translates the request to the appropriate provider's API
        and returns a standardized response format.

        Args:
            prompt: The input prompt
            model: Model to use (e.g., 'gpt-4', 'claude-3', 'command-nightly')
                  Use provider/model format for specific providers
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters
                     (passed through to LiteLLM)

        Returns:
            LLMResponse instance with standardized usage information

        Raises:
            LLMProviderError: If there's an error from the provider
        """
        try:
            # Use default model if not specified
            if not model:
                model = self.default_model

            # Prepare messages
            system_message = kwargs.get("system_message", "")
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})

            # Filter out known kwargs that shouldn't be passed to LiteLLM
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k not in ["system_message"]
            }

            # Generate response using LiteLLM
            response = litellm.completion(  # type: ignore[attr-defined]
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **filtered_kwargs,
            )

            # Extract text
            text = response.choices[0].message.content

            # Extract usage information
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            return LLMResponse(
                text=text,
                model=model or self.default_model,
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            # LiteLLM maps exceptions to OpenAI-compatible ones
            # All LiteLLM exceptions inherit from OpenAI exception types
            raise LLMProviderError(
                f"LiteLLM error: {e}",
                details={
                    "error_type": type(e).__name__,
                    "provider": "litellm",
                    "model": model or self.default_model,
                },
            ) from e

    def stream_generate(
        self,
        prompt: str,
        callback: Callable[[str], None],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: object,
    ) -> LLMResponse:
        """Stream text generation from the LLM using LiteLLM.

        Streams tokens as they are generated and calls the callback function
        for each chunk. LiteLLM handles streaming across all supported providers.

        Args:
            prompt: The input prompt
            callback: Callback function to receive generated text chunks
            model: Model to use (e.g., 'gpt-4', 'claude-3', 'command-nightly')
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters
                     (passed through to LiteLLM)

        Returns:
            LLMResponse instance with the complete generated text and usage info

        Raises:
            LLMProviderError: If there's an error from the provider
        """
        try:
            # Use default model if not specified
            if not model:
                model = self.default_model

            # Prepare messages
            system_message = kwargs.get("system_message", "")
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})

            # Filter out known kwargs that shouldn't be passed to LiteLLM
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k not in ["system_message"]
            }

            # Generate streaming response using LiteLLM
            response = litellm.completion(  # type: ignore[attr-defined]
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **filtered_kwargs,
            )

            # Variables to collect the response
            full_text = ""
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            # Stream the response
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    chunk_text = chunk.choices[0].delta.content
                    full_text += chunk_text
                    
                    # Call the callback with the chunk
                    callback(chunk_text)
                
                # Check for usage information in the chunk
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    usage.update({
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    })

            # If no usage info was provided, use approximation
            if usage["total_tokens"] == 0:
                # Rough approximation: 1 token ≈ 4 characters
                usage["prompt_tokens"] = len(prompt) // 4
                usage["completion_tokens"] = len(full_text) // 4
                usage["total_tokens"] = (
                    usage["prompt_tokens"] + usage["completion_tokens"]
                )

            return LLMResponse(
                text=full_text,
                model=model or self.default_model,
                usage=usage,
                raw_response=None,  # Can't return the streaming response
            )

        except Exception as e:
            # LiteLLM maps exceptions to OpenAI-compatible ones
            # All LiteLLM exceptions inherit from OpenAI exception types
            raise LLMProviderError(
                f"LiteLLM streaming error: {e}",
                details={
                    "error_type": type(e).__name__,
                    "provider": "litellm",
                    "model": model or self.default_model,
                },
            ) from e


# Register the provider
register_provider("litellm", LiteLLMClient)