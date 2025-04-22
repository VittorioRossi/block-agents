"""Script to list all registered blocks and their required/optional inputs."""

import json

import block_agents.blocks  # Ensure all blocks are registered
from block_agents.core.registry import BlockRegistry

OUTPUT_FILE = "blocks_list.json"

def main() -> None:
    blocks_info = {}
    for block_type, block_class in BlockRegistry.get_all().items():
        try:
            # Instantiate with minimal config
            block = block_class(block_id="example_id", config={})
            required = list(block.get_required_inputs())
            optional = list(block.get_optional_inputs())
            doc = block.get_description() if hasattr(block, "get_description") else block_class.__doc__
            blocks_info[block_type] = {
                "required_inputs": required,
                "optional_inputs": optional,
                "description": doc.strip() if doc else ""
            }
        except Exception as e:
            blocks_info[block_type] = {"error": str(e)}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(blocks_info, f, indent=2)
    print(f"Block list written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
