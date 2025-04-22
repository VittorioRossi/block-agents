"""Text-related blocks for the block-based agentic pipeline system."""

from typing import Any, Dict, Optional, Set

from block_agents.core.block import Block
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError
from block_agents.core.registry import register_block


@register_block("text_input")
class TextInputBlock(Block):
    """Block for providing text input to a pipeline.

    This block allows users to provide text input that can be used by other blocks in the pipeline.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new TextInputBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get default text from config
        self.default_text = config.get("default_text", "")
        
        # Get format options
        self.format_options = config.get("format_options", {})

    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, str]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the text
        """
        # Get text from inputs or default
        text = inputs.get("text", self.default_text)
        
        # Log the input
        context.log(self.id, f"Received text input: {text[:50]}..." if len(text) > 50 else text)
        
        return {"text": text}

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Text input is optional (can use default)
        if "text" in inputs and not isinstance(inputs["text"], str):
            raise InputValidationError(
                "Input 'text' must be a string",
                block_id=self.id,
                details={"input_type": type(inputs["text"]).__name__},
            )

    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        return set()

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return {"text"}


@register_block("text_formatter")
class TextFormatterBlock(Block):
    """Block for formatting text.

    This block allows users to format text in various ways, such as:
    - Converting to uppercase or lowercase
    - Trimming whitespace
    - Adding prefixes or suffixes
    - Replacing text
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new TextFormatterBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get format options
        self.case = config.get("case")  # "upper", "lower", "title", "sentence"
        self.trim = config.get("trim", False)
        self.prefix = config.get("prefix", "")
        self.suffix = config.get("suffix", "")
        self.replace = config.get("replace", {})  # {"from": "to"}

    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, str]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the formatted text
        """
        # Get text from inputs
        text = inputs.get("text", "")
        
        # Apply formatting
        if self.trim:
            text = text.strip()
            
        if self.case == "upper":
            text = text.upper()
        elif self.case == "lower":
            text = text.lower()
        elif self.case == "title":
            text = text.title()
        elif self.case == "sentence":
            if text:
                text = text[0].upper() + text[1:].lower()
                
        # Apply replacements
        for from_text, to_text in self.replace.items():
            text = text.replace(from_text, to_text)
            
        # Add prefix and suffix
        text = self.prefix + text + self.suffix
        
        # Log the output
        context.log(self.id, f"Formatted text: {text[:50]}..." if len(text) > 50 else text)
        
        return {"text": text}

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        if "text" not in inputs:
            raise InputValidationError(
                "Required input 'text' not found",
                block_id=self.id,
            )
            
        if not isinstance(inputs["text"], str):
            raise InputValidationError(
                "Input 'text' must be a string",
                block_id=self.id,
                details={"input_type": type(inputs["text"]).__name__},
            )

    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        return {"text"}

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return set()


@register_block("text_joiner")
class TextJoinerBlock(Block):
    """Block for joining multiple text inputs.

    This block allows users to join multiple text inputs into a single text output,
    with optional separators, prefixes, and suffixes.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new TextJoinerBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get join options
        self.separator = config.get("separator", "\n")
        self.prefix = config.get("prefix", "")
        self.suffix = config.get("suffix", "")
        self.input_keys = config.get("input_keys", [])

    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, str]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the joined text
        """
        # Get texts to join
        if self.input_keys:
            # Join specific keys
            texts = []
            for key in self.input_keys:
                if key in inputs and isinstance(inputs[key], str):
                    texts.append(inputs[key])
        else:
            # Join all string values
            texts = [
                value for value in inputs.values()
                if isinstance(value, str)
            ]
        
        # Join texts
        joined_text = self.separator.join(texts)
        
        # Add prefix and suffix
        joined_text = self.prefix + joined_text + self.suffix
        
        # Log the output
        context.log(self.id, f"Joined {len(texts)} texts")
        
        return {"text": joined_text}

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Check that at least one string input is available
        if self.input_keys:
            for key in self.input_keys:
                if key in inputs and isinstance(inputs[key], str):
                    return
                    
            raise InputValidationError(
                f"None of the specified input keys {self.input_keys} found with string values",
                block_id=self.id,
            )
        else:
            for value in inputs.values():
                if isinstance(value, str):
                    return
                    
            raise InputValidationError(
                "No string inputs found",
                block_id=self.id,
            )

    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        return set(self.input_keys) if self.input_keys else set()

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        return set()