"""Block implementations for the block-based agentic pipeline system."""

# Import all block modules to ensure decorators are processed
from block_agents.blocks import file
from block_agents.blocks import text  
from block_agents.blocks import llm
from block_agents.blocks import output
from block_agents.blocks import rag
from block_agents.blocks import repeater
from block_agents.blocks import script
from block_agents.blocks import json_schema