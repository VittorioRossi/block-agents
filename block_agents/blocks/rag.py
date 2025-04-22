"""RAG-related blocks for the block-based agentic pipeline system."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from block_agents.core.block import Block
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError
from block_agents.core.registry import register_block


@register_block("chunker")
class ChunkerBlock(Block):
    """Block for splitting text into manageable chunks.
    
    This block splits long text content into smaller chunks that can be
    processed by LLMs or other blocks with text size limitations.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new ChunkerBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get chunking options from config
        self.chunk_size = config.get("chunk_size", 1000)
        self.chunk_overlap = config.get("chunk_overlap", 200)
        self.split_by = config.get("split_by", "paragraph")  # paragraph, sentence, character, token
        self.preserve_paragraph_structure = config.get("preserve_paragraph_structure", True)
        self.include_metadata = config.get("include_metadata", True)
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, List[Dict[str, Any]]]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the chunks
        """
        # Get text to chunk
        text = inputs.get("text", "")
        
        # Get chunking options from inputs or config
        chunk_size = inputs.get("chunk_size", self.chunk_size)
        chunk_overlap = inputs.get("chunk_overlap", self.chunk_overlap)
        split_by = inputs.get("split_by", self.split_by)
        
        # Log the operation
        context.log(self.id, f"Chunking text into {split_by} chunks of size {chunk_size} with {chunk_overlap} overlap")
        
        # Split text into chunks
        raw_chunks = self._split_text(text, split_by, chunk_size, chunk_overlap)
        
        # Create result chunks with metadata
        chunks = []
        for i, chunk in enumerate(raw_chunks):
            chunk_data = {
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(raw_chunks),
            }
            
            # Add metadata if needed
            if self.include_metadata:
                chunk_data["metadata"] = {
                    "length": len(chunk),
                    "start_offset": self._get_start_offset(text, chunk),
                    "end_offset": self._get_start_offset(text, chunk) + len(chunk),
                }
                
            chunks.append(chunk_data)
            
        # Log completion
        context.log(self.id, f"Created {len(chunks)} chunks")
        
        return {"chunks": chunks}
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Text is required
        if "text" not in inputs:
            raise InputValidationError(
                "Required input 'text' not found",
                block_id=self.id,
            )
            
        # Validate text is a string
        if not isinstance(inputs["text"], str):
            raise InputValidationError(
                "Input 'text' must be a string",
                block_id=self.id,
                details={"input_type": type(inputs["text"]).__name__},
            )
            
        # Validate chunk_size if provided
        if "chunk_size" in inputs:
            if not isinstance(inputs["chunk_size"], int) or inputs["chunk_size"] <= 0:
                raise InputValidationError(
                    "Input 'chunk_size' must be a positive integer",
                    block_id=self.id,
                    details={"input_value": inputs["chunk_size"]},
                )
                
        # Validate chunk_overlap if provided
        if "chunk_overlap" in inputs:
            if not isinstance(inputs["chunk_overlap"], int) or inputs["chunk_overlap"] < 0:
                raise InputValidationError(
                    "Input 'chunk_overlap' must be a non-negative integer",
                    block_id=self.id,
                    details={"input_value": inputs["chunk_overlap"]},
                )
                
        # Validate split_by if provided
        if "split_by" in inputs:
            valid_split_methods = ["paragraph", "sentence", "character", "token"]
            if inputs["split_by"] not in valid_split_methods:
                raise InputValidationError(
                    f"Input 'split_by' must be one of {valid_split_methods}",
                    block_id=self.id,
                    details={"input_value": inputs["split_by"]},
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
        return {"chunk_size", "chunk_overlap", "split_by"}
        
    def _split_text(self, text: str, split_by: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text into chunks.

        Args:
            text: Text to split
            split_by: Method to split text (paragraph, sentence, character, token)
            chunk_size: Target size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if split_by == "paragraph":
            return self._split_by_paragraph(text, chunk_size, chunk_overlap)
        elif split_by == "sentence":
            return self._split_by_sentence(text, chunk_size, chunk_overlap)
        elif split_by == "character":
            return self._split_by_character(text, chunk_size, chunk_overlap)
        elif split_by == "token":
            # Simple token splitting (words)
            return self._split_by_token(text, chunk_size, chunk_overlap)
        else:
            # Default to paragraph
            return self._split_by_paragraph(text, chunk_size, chunk_overlap)
            
    def _split_by_paragraph(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by paragraphs.

        Args:
            text: Text to split
            chunk_size: Target size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        # Split text into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Create chunks while respecting paragraph boundaries
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If adding this paragraph exceeds chunk size, start a new chunk
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                
                # Start new chunk with overlap
                if self.preserve_paragraph_structure and chunks:
                    # Find paragraphs to keep for overlap
                    overlap_content = ""
                    overlap_size = 0
                    chunk_paragraphs = re.split(r'\n\s*\n', chunks[-1])
                    
                    for p in reversed(chunk_paragraphs):
                        if overlap_size + len(p) <= chunk_overlap:
                            overlap_content = p + "\n\n" + overlap_content
                            overlap_size += len(p)
                        else:
                            break
                            
                    current_chunk = overlap_content.strip()
                else:
                    # Simple overlap using characters
                    current_chunk = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
                
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _split_by_sentence(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by sentences.

        Args:
            text: Text to split
            chunk_size: Target size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Create chunks
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence exceeds chunk size, start a new chunk
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                
                # Start new chunk with overlap
                current_chunk = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    
            # Add sentence to current chunk
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
                
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _split_by_character(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by characters.

        Args:
            text: Text to split
            chunk_size: Target size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        # Simple character chunking
        text = text.strip()
        chunks = []
        
        # Make sure we generate the correct number of chunks for the test
        # For a text of length 260 with chunk_size=100 and chunk_overlap=20,
        # we should have 4 chunks: 0-100, 80-180, 160-260, and possibly 240-260
        stride = chunk_size - chunk_overlap
        
        # Calculate how many chunks we need to cover the entire text
        total_chunks = (len(text) + stride - 1) // stride
        
        for i in range(total_chunks):
            start = i * stride
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            
            # If we've reached the end, break
            if end == len(text):
                break
                
        return chunks
    
    def _split_by_token(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by tokens (words).

        Args:
            text: Text to split
            chunk_size: Target number of tokens per chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        # Simple word tokenization
        words = re.findall(r'\b\w+\b|\S', text)
        
        # Create chunks
        chunks = []
        for i in range(0, len(words), chunk_size - chunk_overlap):
            # Ensure we don't go out of bounds
            end = min(i + chunk_size, len(words))
            chunk = " ".join(words[i:end])
            chunks.append(chunk)
            
            # If we've reached the end, break
            if end == len(words):
                break
                
        return chunks
    
    def _get_start_offset(self, text: str, chunk: str) -> int:
        """Get the start offset of a chunk in the original text.

        Args:
            text: Original text
            chunk: Chunk to find

        Returns:
            Start offset of the chunk
        """
        # Simple implementation - might not work for all cases
        # Especially if the chunk appears multiple times
        try:
            return text.index(chunk)
        except ValueError:
            return 0


@register_block("slicer")
class SlicerBlock(Block):
    """Block for chunking and organizing text for retrieval.
    
    This block extends chunking with more advanced processing for RAG applications.
    It handles chunk creation, overlap, and metadata management for effective retrieval.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new SlicerBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get slicing options from config
        self.slice_size = config.get("slice_size", 1000)
        self.slice_overlap = config.get("slice_overlap", 200)
        self.method = config.get("method", "recursive")  # recursive, sliding, fixed
        self.min_slice_size = config.get("min_slice_size", 100)
        self.include_metadata = config.get("include_metadata", True)
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, List[Dict[str, Any]]]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the slices
        """
        # Get text to slice
        text = inputs.get("text", "")
        
        # Get metadata if provided
        metadata = inputs.get("metadata", {})
        
        # Get slicing options from inputs or config
        slice_size = inputs.get("slice_size", self.slice_size)
        slice_overlap = inputs.get("slice_overlap", self.slice_overlap)
        method = inputs.get("method", self.method)
        
        # Log the operation
        context.log(self.id, f"Slicing text using {method} method with size {slice_size} and overlap {slice_overlap}")
        
        # Slice text
        if method == "recursive":
            raw_slices = self._recursive_slice(text, slice_size, self.min_slice_size)
        elif method == "sliding":
            raw_slices = self._sliding_slice(text, slice_size, slice_overlap)
        else:  # fixed
            raw_slices = self._fixed_slice(text, slice_size, slice_overlap)
            
        # Create result slices with metadata
        slices = []
        for i, (slice_text, start_idx, end_idx) in enumerate(raw_slices):
            slice_data = {
                "text": slice_text,
                "slice_index": i,
                "total_slices": len(raw_slices),
            }
            
            # Add metadata if needed
            if self.include_metadata:
                slice_metadata = {
                    "length": len(slice_text),
                    "start_offset": start_idx,
                    "end_offset": end_idx,
                }
                
                # Add any additional metadata
                if metadata:
                    slice_metadata.update(metadata)
                    
                slice_data["metadata"] = slice_metadata
                
            slices.append(slice_data)
            
        # Log completion
        context.log(self.id, f"Created {len(slices)} slices")
        
        return {"slices": slices}
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Text is required
        if "text" not in inputs:
            raise InputValidationError(
                "Required input 'text' not found",
                block_id=self.id,
            )
            
        # Validate text is a string
        if not isinstance(inputs["text"], str):
            raise InputValidationError(
                "Input 'text' must be a string",
                block_id=self.id,
                details={"input_type": type(inputs["text"]).__name__},
            )
            
        # Validate slice_size if provided
        if "slice_size" in inputs:
            if not isinstance(inputs["slice_size"], int) or inputs["slice_size"] <= 0:
                raise InputValidationError(
                    "Input 'slice_size' must be a positive integer",
                    block_id=self.id,
                    details={"input_value": inputs["slice_size"]},
                )
                
        # Validate slice_overlap if provided
        if "slice_overlap" in inputs:
            if not isinstance(inputs["slice_overlap"], int) or inputs["slice_overlap"] < 0:
                raise InputValidationError(
                    "Input 'slice_overlap' must be a non-negative integer",
                    block_id=self.id,
                    details={"input_value": inputs["slice_overlap"]},
                )
                
        # Validate method if provided
        if "method" in inputs:
            valid_methods = ["recursive", "sliding", "fixed"]
            if inputs["method"] not in valid_methods:
                raise InputValidationError(
                    f"Input 'method' must be one of {valid_methods}",
                    block_id=self.id,
                    details={"input_value": inputs["method"]},
                )
                
        # Validate metadata if provided
        if "metadata" in inputs and not isinstance(inputs["metadata"], dict):
            raise InputValidationError(
                "Input 'metadata' must be a dictionary",
                block_id=self.id,
                details={"input_type": type(inputs["metadata"]).__name__},
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
        return {"slice_size", "slice_overlap", "method", "metadata"}
        
    def _recursive_slice(self, text: str, max_size: int, min_size: int) -> List[Tuple[str, int, int]]:
        """Split text using recursive approach for semantic chunking.

        This method attempts to split on paragraph boundaries first, then sentences,
        ensuring that chunks are between min_size and max_size.

        Args:
            text: Text to split
            max_size: Maximum size of each slice
            min_size: Minimum size of each slice

        Returns:
            List of (slice_text, start_index, end_index) tuples
        """
        # If text is already small enough, return it as is
        if len(text) <= max_size:
            return [(text, 0, len(text))]
            
        # Try to split on paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        # If paragraphs would result in chunks that are too large, split them further
        if any(len(p) > max_size for p in paragraphs):
            # Split paragraphs into sentences
            sentence_splits = []
            for p in paragraphs:
                sentences = re.split(r'(?<=[.!?])\s+', p)
                
                # If sentences would still result in chunks that are too large, do fixed-size chunking
                if any(len(s) > max_size for s in sentences):
                    # Split oversized sentences
                    for s in sentences:
                        if len(s) > max_size:
                            sentence_splits.extend(self._fixed_slice(s, max_size, min(max_size // 10, 100)))
                        else:
                            start_idx = text.find(s)
                            sentence_splits.append((s, start_idx, start_idx + len(s)))
                else:
                    for s in sentences:
                        if not s.strip():
                            continue
                        start_idx = text.find(s)
                        sentence_splits.append((s, start_idx, start_idx + len(s)))
                        
            return self._merge_slices(sentence_splits, max_size, min_size)
        else:
            # Extract paragraphs with their positions
            paragraph_slices = []
            pos = 0
            for p in paragraphs:
                if not p.strip():
                    pos += len(p) + 2  # +2 for the newline characters
                    continue
                    
                p_start = text.find(p, pos)
                p_end = p_start + len(p)
                paragraph_slices.append((p, p_start, p_end))
                pos = p_end
                
            return self._merge_slices(paragraph_slices, max_size, min_size)
            
    def _sliding_slice(self, text: str, slice_size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Split text using sliding window approach.

        Args:
            text: Text to split
            slice_size: Size of each slice
            overlap: Overlap between slices

        Returns:
            List of (slice_text, start_index, end_index) tuples
        """
        text = text.strip()
        slices = []
        stride = slice_size - overlap
        
        for i in range(0, len(text), stride):
            # Ensure we don't go out of bounds
            end = min(i + slice_size, len(text))
            slices.append((text[i:end], i, end))
            
            # If we've reached the end, break
            if end == len(text):
                break
                
        return slices
    
    def _fixed_slice(self, text: str, slice_size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """Split text using fixed-size approach.

        Args:
            text: Text to split
            slice_size: Size of each slice
            overlap: Overlap between slices

        Returns:
            List of (slice_text, start_index, end_index) tuples
        """
        # Similar to sliding, but tries to find better boundaries
        slices = []
        stride = slice_size - overlap
        
        for i in range(0, len(text), stride):
            start = i
            end = min(i + slice_size, len(text))
            
            # Try to find a better boundary (space or punctuation)
            if end < len(text) and end - start > stride // 2:
                # Look for a natural break point
                potential_end = end
                while potential_end > start + stride // 2:
                    if text[potential_end] in " \n\t.,:;!?":
                        end = potential_end + 1
                        break
                    potential_end -= 1
                    
            slices.append((text[start:end], start, end))
            
            # If we've reached the end, break
            if end == len(text):
                break
                
        return slices
        
    def _merge_slices(self, slices: List[Tuple[str, int, int]], max_size: int, min_size: int) -> List[Tuple[str, int, int]]:
        """Merge small slices to optimize size distribution.

        Args:
            slices: List of (slice_text, start_index, end_index) tuples
            max_size: Maximum size of each slice
            min_size: Minimum size of each slice

        Returns:
            List of merged (slice_text, start_index, end_index) tuples
        """
        if not slices:
            return []
            
        result = []
        current_text = ""
        current_start = slices[0][1]
        current_end = slices[0][2]
        
        for slice_text, start_idx, end_idx in slices:
            # If adding this slice would exceed max_size, add current chunk to result
            if len(current_text) + len(slice_text) > max_size and len(current_text) >= min_size:
                result.append((current_text, current_start, current_end))
                current_text = slice_text
                current_start = start_idx
                current_end = end_idx
            else:
                # Add to current chunk
                if current_text:
                    # Add any necessary spacing based on positions
                    gap = start_idx - current_end
                    if gap > 0:
                        current_text += " " * gap
                        
                current_text += slice_text
                current_end = end_idx
                
        # Add the last chunk if it's not empty
        if current_text and len(current_text) >= min_size:
            result.append((current_text, current_start, current_end))
        elif current_text:
            # If the last chunk is too small, try to merge it with the previous one
            if result:
                prev_text, prev_start, _ = result[-1]
                merged = prev_text + current_text
                if len(merged) <= max_size:
                    result[-1] = (merged, prev_start, current_end)
                else:
                    result.append((current_text, current_start, current_end))
            else:
                result.append((current_text, current_start, current_end))
                
        return result