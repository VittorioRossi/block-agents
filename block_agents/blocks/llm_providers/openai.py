"""OpenAI provider for LLM integration."""

from typing import Any, Callable, Dict, Optional

import openai

from block_agents.core.client_manager import (
    BaseLLMClient,
    LLMResponse,
    register_provider,
)
from block_agents.core.config import Config
from block_agents.core.errors import LLMProviderError


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI LLM provider."""

    def __init__(self, config: Config, provider: str = "openai"):
        """Initialize a new OpenAIClient.

        Args:
            config: Configuration instance
            provider: Provider name
        """
        super().__init__(config, provider)
        
        # Create OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)

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
            messages = [{"role": "user", "content": prompt}]
            
            # Add system message if provided
            system_message = kwargs.get("system_message")
            if system_message:
                messages.insert(0, {"role": "system", "content": system_message})
                
            # Generate response
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout_seconds,
                **{k: v for k, v in kwargs.items() if k not in ["system_message"]},
            )
            
            # Extract text
            text = response.choices[0].message.content
            
            # Extract usage
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            return LLMResponse(
                text=text,
                model=model,
                usage=usage,
                raw_response=response,
            )
            
        except openai.OpenAIError as e:
            raise LLMProviderError(
                f"OpenAI error: {e}",
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
            messages = [{"role": "user", "content": prompt}]
            
            # Add system message if provided
            system_message = kwargs.get("system_message")
            if system_message:
                messages.insert(0, {"role": "system", "content": system_message})
                
            # Generate streaming response
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout_seconds,
                stream=True,
                **{k: v for k, v in kwargs.items() if k not in ["system_message"]},
            )
            
            # Variables to collect the response
            full_text = ""
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            # Stream the response
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunk_text = chunk.choices[0].delta.content
                    full_text += chunk_text
                    
                    # Call the callback with the chunk
                    callback(chunk_text)
                    
                    # Increment token count (approximate)
                    usage["completion_tokens"] += 1
                    
            # Approximate prompt tokens
            usage["prompt_tokens"] = len(prompt) // 4  # Very rough approximation
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
            
            return LLMResponse(
                text=full_text,
                model=model,
                usage=usage,
                raw_response=None,  # Can't return the streaming response
            )
            
        except openai.OpenAIError as e:
            raise LLMProviderError(
                f"OpenAI error: {e}",
                details={"error_type": type(e).__name__},
            )
        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                details={"error_type": type(e).__name__},
            )


# Register the provider
register_provider("openai", OpenAIClient)