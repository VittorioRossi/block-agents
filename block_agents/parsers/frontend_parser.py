"""Parser for frontend workflow format to internal pipeline format."""

import uuid
from typing import Any, Dict, List, Optional, Set

from block_agents.core.errors import PipelineDefinitionError


class FrontendParser:
    """Parser to convert frontend workflow format to internal pipeline format."""

    @staticmethod
    def parse(frontend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse frontend workflow format to internal pipeline format.

        Args:
            frontend_data: Frontend workflow definition

        Returns:
            Internal pipeline definition

        Raises:
            PipelineDefinitionError: If the frontend data is invalid
        """
        try:
            # Validate input structure
            FrontendParser._validate_frontend_data(frontend_data)
            
            # Extract main components
            name = frontend_data.get("name", "Unnamed Workflow")
            description = frontend_data.get("description", "")
            definition = frontend_data["definition"]
            
            nodes = definition["nodes"]
            links = definition["links"]
            
            # Convert nodes to blocks
            blocks = FrontendParser._convert_nodes_to_blocks(nodes)
            
            # Build dependency relationships from links
            FrontendParser._build_block_relationships(blocks, links)
            
            # Generate pipeline ID if not provided
            pipeline_id = frontend_data.get("pipeline_id", str(uuid.uuid4()))
            
            # Create internal pipeline format
            pipeline_def = {
                "pipeline_id": pipeline_id,
                "name": name,
                "description": description,
                "stream_config": {
                    "enabled": True,
                    "log_level": "info",
                    "include_block_types": [],
                    "throttle_ms": 100,
                },
                "blocks": blocks,
            }
            
            # Identify output block (last block in the workflow)
            output_block_id = FrontendParser._find_output_block(blocks, links)
            if output_block_id:
                pipeline_def["output"] = output_block_id
            
            return pipeline_def
            
        except Exception as e:
            if isinstance(e, PipelineDefinitionError):
                raise
            raise PipelineDefinitionError(f"Error parsing frontend data: {e}") from e

    @staticmethod
    def _validate_frontend_data(data: Dict[str, Any]) -> None:
        """Validate frontend data structure.

        Args:
            data: Frontend data to validate

        Raises:
            PipelineDefinitionError: If data is invalid
        """
        if not isinstance(data, dict):
            raise PipelineDefinitionError("Frontend data must be a dictionary")
        
        if "definition" not in data:
            raise PipelineDefinitionError("Frontend data must contain 'definition'")
        
        definition = data["definition"]
        if not isinstance(definition, dict):
            raise PipelineDefinitionError("'definition' must be a dictionary")
        
        if "nodes" not in definition:
            raise PipelineDefinitionError("Definition must contain 'nodes'")
        
        if "links" not in definition:
            raise PipelineDefinitionError("Definition must contain 'links'")
        
        if not isinstance(definition["nodes"], list):
            raise PipelineDefinitionError("'nodes' must be a list")
        
        if not isinstance(definition["links"], list):
            raise PipelineDefinitionError("'links' must be a list")

    @staticmethod
    def _convert_nodes_to_blocks(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert frontend nodes to internal blocks.

        Args:
            nodes: List of frontend nodes

        Returns:
            List of internal blocks
        """
        blocks = []
        
        for node in nodes:
            # Extract basic information
            node_id = node.get("id")
            if not node_id:
                raise PipelineDefinitionError("Node must have an 'id'")
            
            node_type = node.get("node_type")
            if not node_type:
                raise PipelineDefinitionError(f"Node {node_id} must have a 'node_type'")
            
            # Map frontend node types to internal block types
            block_type = FrontendParser._map_node_type_to_block_type(node_type)
            
            # Extract configuration
            config = node.get("config", {})
            
            # Create internal block
            block = {
                "id": node_id,
                "type": block_type,
                "config": FrontendParser._convert_node_config(config, node_type),
                "next": [],  # Will be populated by _build_block_relationships
            }
            
            blocks.append(block)
        
        return blocks

    @staticmethod
    def _map_node_type_to_block_type(node_type: str) -> str:
        """Map frontend node type to internal block type.

        Args:
            node_type: Frontend node type

        Returns:
            Internal block type
        """
        mapping = {
            "inputNode": "text_input",
            "llmNode": "llm",
            "codeNode": "python_script",  # Custom scraping block
        }
        
        return mapping[node_type]  # Default to script for unknown types

    @staticmethod
    def _convert_node_config(config: Dict[str, Any], node_type: str) -> Dict[str, Any]:
        """Convert frontend node config to internal block config.

        Args:
            config: Frontend node configuration
            node_type: Frontend node type

        Returns:
            Internal block configuration
        """
        if node_type == "SingleLLMCallNode":
            # Convert LLM node configuration
            llm_info = config.get("llm_info", {})
            return {
                "provider": FrontendParser._extract_llm_provider(
                    llm_info.get("model", "")
                ),
                "model": FrontendParser._extract_llm_model(llm_info.get("model", "")),
                "temperature": llm_info.get("temperature", 0.7),
                "max_tokens": llm_info.get("max_tokens", 4096),
                "system_message": config.get("system_message", ""),
                "prompt": config.get("user_message", ""),
                "top_p": llm_info.get("top_p", 0.9),
            }
        elif node_type == "InputNode":
            # Convert input node configuration
            return {
                "output_schema": config.get("output_schema", {}),
                "default_values": {},  # Can be populated from test_inputs if needed
            }
        else:
            # For other node types, pass config as-is for now
            # These would need custom block implementations
            return config

    @staticmethod
    def _extract_llm_provider(model_string: str) -> str:
        """Extract LLM provider from model string.

        Args:
            model_string: Model string like "openai/gpt-4" or "anthropic/claude-3"

        Returns:
            Provider name
        """
        if "/" in model_string:
            return model_string.split("/")[0]
        
        # Fallback mapping for common models
        if "gpt" in model_string.lower():
            return "openai"
        elif "claude" in model_string.lower():
            return "anthropic"
        elif "gemini" in model_string.lower():
            return "google"
        
        return "openai"  # Default fallback

    @staticmethod
    def _extract_llm_model(model_string: str) -> str:
        """Extract LLM model from model string.

        Args:
            model_string: Model string like "openai/gpt-4" or "anthropic/claude-3"

        Returns:
            Model name
        """
        if "/" in model_string:
            return model_string.split("/", 1)[1]
        
        return model_string

    @staticmethod
    def _build_block_relationships(
        blocks: List[Dict[str, Any]], links: List[Dict[str, Any]]
    ) -> None:
        """Build block relationships from frontend links.

        Args:
            blocks: List of blocks to update
            links: List of frontend links

        Raises:
            PipelineDefinitionError: If links reference non-existent blocks
        """
        # Create a mapping from block ID to block for easy lookup
        block_map = {block["id"]: block for block in blocks}
        
        # Build relationships
        for link in links:
            source_id = link.get("source_id")
            target_id = link.get("target_id")
            
            if not source_id or not target_id:
                continue  # Skip invalid links
            
            if source_id not in block_map:
                raise PipelineDefinitionError(
                    f"Link references non-existent source block: {source_id}"
                )
            
            if target_id not in block_map:
                raise PipelineDefinitionError(
                    f"Link references non-existent target block: {target_id}"
                )
            
            # Add target to source's next list
            source_block = block_map[source_id]
            if target_id not in source_block["next"]:
                source_block["next"].append(target_id)

    @staticmethod
    def _find_output_block(
        blocks: List[Dict[str, Any]], links: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find the output block (block with no outgoing links).

        Args:
            blocks: List of blocks
            links: List of links

        Returns:
            ID of the output block, or None if not found
        """
        # Get all source IDs (blocks that have outgoing links)
        source_ids: Set[str] = {
            link["source_id"] for link in links if link.get("source_id")
        }
        
        # Find blocks that are not sources (no outgoing links)
        output_candidates = [
            block["id"] for block in blocks if block["id"] not in source_ids
        ]
        
        # Return the first candidate, or None if no candidates
        return output_candidates[0] if output_candidates else None