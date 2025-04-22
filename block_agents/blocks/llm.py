"""LLM integration blocks for the block-based agentic pipeline system."""

from typing import Any, Dict, List, Optional, Set

# Import providers to register them
import block_agents.blocks.llm_providers  # noqa
from block_agents.core.block import Block
from block_agents.core.context import Context
from block_agents.core.errors import BlockRuntimeError, InputValidationError
from block_agents.core.registry import register_block


@register_block("llm")
class LLMBlock(Block):
    """Block for using language models to generate text.

    This block allows users to send prompts to language models and receive generated text.
    It supports various LLM providers and models.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new LLMBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get LLM options
        self.provider = config.get("provider")  # Use default if not specified
        self.model = config.get("model")  # Use provider's default if not specified
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
        self.stream = config.get("stream", True)
        
        # Get prompt configuration
        self.system_message = config.get("system_message", "")
        self.prompt_template = config.get("prompt_template", "{prompt}")
        
        # Optional mappings for input and output
        self.input_key = config.get("input_key", "prompt")
        self.output_key = config.get("output_key", "text")

    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the generated text

        Raises:
            BlockRuntimeError: If there's a runtime error
        """
        # Get the client manager
        client_manager = context.get_client_manager()
        if not client_manager:
            raise BlockRuntimeError(
                "LLM client manager not found in context",
                block_id=self.id,
            )
            
        # Get the prompt from inputs
        prompt = inputs.get(self.input_key, "")
        
        # Format the prompt using the template
        try:
            formatted_prompt = self.prompt_template.format(
                prompt=prompt,
                **{k: v for k, v in inputs.items() if k != self.input_key}
            )
        except KeyError as e:
            raise BlockRuntimeError(
                f"Error formatting prompt: missing key {e}",
                block_id=self.id,
                details={"prompt_template": self.prompt_template},
            )
            
        # Log the formatted prompt
        context.log(self.id, f"Sending prompt: {formatted_prompt[:100]}..." if len(formatted_prompt) > 100 else formatted_prompt)
        
        # Additional parameters for the LLM
        additional_params = {}
        if self.system_message:
            additional_params["system_message"] = self.system_message
            
        try:
            # Generate or stream based on configuration
            if self.stream:
                # Create a callback to report progress
                collected_text = []
                
                def progress_callback(chunk: str) -> None:
                    collected_text.append(chunk)
                    current_text = "".join(collected_text)
                    
                    # Report progress (simple approximation)
                    progress = min(1.0, len(collected_text) / 10.0)  # Assume around 10 chunks
                    self.report_progress(context, progress, current_text)
                
                # Stream generation
                response = client_manager.stream_generate(
                    prompt=formatted_prompt,
                    callback=progress_callback,
                    provider=self.provider,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    **additional_params,
                )
                
                text = response.text
                
            else:
                # Standard generation
                response = client_manager.generate(
                    prompt=formatted_prompt,
                    provider=self.provider,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    **additional_params,
                )
                
                text = response.text
            
            # Log token usage
            context.log(
                self.id,
                f"Token usage: {response.usage['total_tokens']} total, "
                f"{response.usage['prompt_tokens']} prompt, "
                f"{response.usage['completion_tokens']} completion",
            )
            
            # Return the result
            result = {
                self.output_key: text,
                "model": response.model,
                "usage": response.usage,
            }
            
            return result
            
        except Exception as e:
            raise BlockRuntimeError(
                f"Error generating text: {e}",
                block_id=self.id,
                details={"error_type": type(e).__name__},
            )

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        if self.input_key not in inputs:
            raise InputValidationError(
                f"Required input '{self.input_key}' not found",
                block_id=self.id,
            )
            
        if not isinstance(inputs[self.input_key], str):
            raise InputValidationError(
                f"Input '{self.input_key}' must be a string",
                block_id=self.id,
                details={"input_type": type(inputs[self.input_key]).__name__},
            )
            
        # Check that all template variables are available
        try:
            self.prompt_template.format(
                prompt=inputs[self.input_key],
                **{k: v for k, v in inputs.items() if k != self.input_key}
            )
        except KeyError as e:
            raise InputValidationError(
                f"Prompt template requires key {e} which is not in inputs",
                block_id=self.id,
                details={"prompt_template": self.prompt_template},
            )

    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        # Get required keys from prompt template
        required_keys = {self.input_key}
        
        # Find all format variables in the template
        import re
        format_vars = re.findall(r"\{([^}]+)\}", self.prompt_template)
        
        # Add all variables except {prompt} which is handled separately
        for var in format_vars:
            if var != "prompt":
                required_keys.add(var)
                
        return required_keys

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return set()