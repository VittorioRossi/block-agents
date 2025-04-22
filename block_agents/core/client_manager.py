"""LLM client manager for the block-based agentic pipeline system."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from block_agents.core.config import Config
from block_agents.core.errors import ConfigurationError, LLMProviderError


class LLMResponse:
    """Response from an LLM provider."""

    def __init__(self, text: str, model: str, usage: Dict[str, int], raw_response: Any = None):
        """Initialize a new LLMResponse.

        Args:
            text: The generated text
            model: The model used for generation
            usage: Token usage statistics
            raw_response: The raw response from the provider
        """
        self.text = text
        self.model = model
        self.usage = usage
        self.raw_response = raw_response


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    def __init__(self, config: Config, provider: str):
        """Initialize a new BaseLLMClient.

        Args:
            config: Configuration instance
            provider: Provider name
        """
        self.config = config
        self.provider = provider
        self.default_model = config.get(f"llm.providers.{provider}.default_model")
        self.timeout_seconds = config.get(f"llm.providers.{provider}.timeout_seconds", 60)

        # Get API key
        self.api_key = config.get_api_key(provider)
        # Providers that don't require an API key
        api_key_optional_providers = ["local", "ollama"]
        if not self.api_key and provider not in api_key_optional_providers:
            raise ConfigurationError(f"API key not found for LLM provider: {provider}")

    @abstractmethod
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
        """
        pass

    @abstractmethod
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
        """
        pass


class LLMClientManager:
    """Manager for LLM clients.

    This class handles:
    - Creating and caching LLM clients
    - Selecting the appropriate provider
    - Providing a unified interface for all providers
    """

    # Registry of provider implementations
    _providers: Dict[str, type] = {}

    # Client cache
    _clients: Dict[str, BaseLLMClient] = {}

    def __init__(self, config: Config):
        """Initialize a new LLMClientManager.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.default_provider = config.get("llm.default_provider", "openai")

    def get_client(self, provider: Optional[str] = None) -> BaseLLMClient:
        """Get a client for the specified provider.

        Args:
            provider: Provider name (defaults to the default provider)

        Returns:
            LLM client instance

        Raises:
            ConfigurationError: If the provider is not supported
        """
        # Use default provider if not specified
        provider = provider or self.default_provider

        # Check if provider is supported
        if provider not in self._providers:
            raise ConfigurationError(f"Unsupported LLM provider: {provider}")

        # Check if client is cached
        if provider not in self._clients:
            # Create and cache client
            client_class = self._providers[provider]
            self._clients[provider] = client_class(self.config, provider)

        return self._clients[provider]

    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text using the specified provider.

        Args:
            prompt: The input prompt
            provider: Provider name (defaults to the default provider)
            model: Model to use (defaults to provider's default model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse instance
        """
        client = self.get_client(provider)
        return client.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def stream_generate(
        self,
        prompt: str,
        callback: Callable[[str], None],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Stream text generation using the specified provider.

        Args:
            prompt: The input prompt
            callback: Callback function to receive generated text
            provider: Provider name (defaults to the default provider)
            model: Model to use (defaults to provider's default model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse instance
        """
        client = self.get_client(provider)
        return client.stream_generate(
            prompt=prompt,
            callback=callback,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    @classmethod
    def register_provider(cls, provider: str, client_class: type) -> None:
        """Register an LLM provider implementation.

        Args:
            provider: Provider name
            client_class: Implementation class
        """
        cls._providers[provider] = client_class


# Register this function for external use
def register_provider(provider: str, client_class: type) -> None:
    """Register an LLM provider implementation.

    Args:
        provider: Provider name
        client_class: Implementation class
    """
    LLMClientManager.register_provider(provider, client_class)