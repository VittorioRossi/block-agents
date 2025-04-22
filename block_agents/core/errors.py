"""Error handling for the block-based agentic pipeline system."""

from typing import Any, Dict, Optional, Type


class BlockAgentError(Exception):
    """Base exception class for all block-agent-backend errors."""

    code: str = "block_agent_error"
    status_code: int = 500

    def __init__(
        self, message: str, block_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """Initialize a new BlockAgentError.

        Args:
            message: Human-readable error message
            block_id: ID of the block that caused the error, if applicable
            details: Additional error details
        """
        self.message = message
        self.block_id = block_id
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary.

        Returns:
            Dictionary representation of the error
        """
        result = {
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.block_id:
            result["block_id"] = self.block_id
        if self.details:
            result["details"] = self.details
        return result


class ConfigurationError(BlockAgentError):
    """Error raised when there's an issue with the configuration."""

    code = "configuration_error"
    status_code = 400


class BlockDefinitionError(BlockAgentError):
    """Error raised when there's an issue with a block definition."""

    code = "block_definition_error"
    status_code = 400


class BlockRuntimeError(BlockAgentError):
    """Error raised when there's a runtime error in a block."""

    code = "block_runtime_error"
    status_code = 500


class PipelineDefinitionError(BlockAgentError):
    """Error raised when there's an issue with a pipeline definition."""

    code = "pipeline_definition_error"
    status_code = 400


class PipelineRuntimeError(BlockAgentError):
    """Error raised when there's a runtime error in a pipeline."""

    code = "pipeline_runtime_error"
    status_code = 500


class InputValidationError(BlockAgentError):
    """Error raised when input validation fails."""

    code = "input_validation_error"
    status_code = 400


class OutputValidationError(BlockAgentError):
    """Error raised when output validation fails."""

    code = "output_validation_error"
    status_code = 500


class BlockTimeoutError(BlockAgentError):
    """Error raised when a block execution times out."""

    code = "timeout_error"
    status_code = 504


class ResourceError(BlockAgentError):
    """Error raised when there's an issue with a resource."""

    code = "resource_error"
    status_code = 500


class LLMProviderError(BlockAgentError):
    """Error raised when there's an issue with an LLM provider."""

    code = "llm_provider_error"
    status_code = 502


class APIError(BlockAgentError):
    """Error raised when there's an issue with the API."""

    code = "api_error"
    status_code = 500


def get_error_class_by_code(code: str) -> Type[BlockAgentError]:
    """Get an error class by its code.

    Args:
        code: The error code

    Returns:
        The error class

    Raises:
        ValueError: If the error code is not recognized
    """
    error_classes = {
        cls.code: cls
        for cls in BlockAgentError.__subclasses__()
        if hasattr(cls, "code")
    }
    if code not in error_classes:
        raise ValueError(f"Unknown error code: {code}")
    return error_classes[code]