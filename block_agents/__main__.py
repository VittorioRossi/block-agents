"""Command-line interface for the block-based agentic pipeline system."""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from block_agents.core.config import Config
from block_agents.core.errors import BlockAgentError
from block_agents.core.pipeline import Pipeline
from block_agents.core.stream import StreamEvent
import block_agents.blocks # Import all blocks to register them

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file isn't valid JSON
    """
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path: str, data: Any) -> None:
    """Save data to a JSON file.

    Args:
        file_path: Path to the JSON file
        data: Data to save
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def print_event(event: StreamEvent) -> None:
    """Print a stream event to the console.

    Args:
        event: The event to print
    """
    # Only print certain event types
    if event.event_type == "block_log":
        level = event.data.get("level", "info")
        message = event.data.get("message", "")
        
        # Format based on log level
        if level == "error":
            print(f"\033[91m[ERROR] {event.block_id}: {message}\033[0m")
        elif level == "warning":
            print(f"\033[93m[WARNING] {event.block_id}: {message}\033[0m")
        elif level == "debug":
            if args.verbose:
                print(f"\033[90m[DEBUG] {event.block_id}: {message}\033[0m")
        else:
            print(f"[INFO] {event.block_id}: {message}")
            
    elif event.event_type == "block_error":
        message = event.data.get("message", "Unknown error")
        error_type = event.data.get("type", "Error")
        print(f"\033[91m[ERROR] {event.block_id}: {error_type}: {message}\033[0m")
        
    elif event.event_type == "block_start":
        if args.verbose:
            print(f"Starting block: {event.block_id}")
            
    elif event.event_type == "block_complete":
        if args.verbose:
            print(f"Completed block: {event.block_id}")
            
    elif event.event_type == "pipeline_start":
        name = event.data.get("name", "")
        pipeline_id = event.data.get("pipeline_id", "")
        print(f"Starting pipeline: {name} (ID: {pipeline_id})")
        
    elif event.event_type == "pipeline_complete":
        execution_time = event.data.get("execution_time", 0)
        print(f"Pipeline completed in {execution_time:.2f} seconds")


def run_pipeline(
    input_file: str,
    output_file: Optional[str] = None,
    config_file: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """Run a pipeline from a JSON input file.

    Args:
        input_file: Path to the input JSON file
        output_file: Path to the output JSON file (optional)
        config_file: Path to the configuration file (optional)
        verbose: Whether to enable verbose logging
    """
    try:
        # Load input data
        data = load_json_file(input_file)
        
        # Extract pipeline definition and input values
        if "pipeline_id" in data and "input_values" in data:
            # Input format with separate pipeline_id and input_values
            pipeline_id = data["pipeline_id"]
            pipeline_def_file = os.path.join(
                os.path.dirname(os.path.abspath(input_file)), 
                f"{pipeline_id}.json"
            )
            if not os.path.exists(pipeline_def_file):
                print(f"Pipeline definition not found: {pipeline_def_file}")
                sys.exit(1)
                
            pipeline_def = load_json_file(pipeline_def_file)
            input_values = data["input_values"]
        else:
            # Assume input file contains both pipeline definition and input values
            pipeline_def = data
            input_values = {}
        
        # Load configuration
        config = Config.load(config_file) if config_file else Config.load()
        
        # Create pipeline
        pipeline = Pipeline(pipeline_def, config)
        
        # Add subscriber for events
        pipeline.add_subscriber(print_event)
        
        # Execute pipeline
        result = pipeline.execute(input_values)
        
        # Save result if output file specified
        if output_file:
            save_json_file(output_file, result)
            print(f"Result saved to: {output_file}")
        elif verbose:
            # Print result in verbose mode
            print("Result:")
            print(json.dumps(result, indent=2))
            
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)
    except BlockAgentError as e:
        print(f"Error: {e}")
        if hasattr(e, "details") and e.details:
            print(f"Details: {e.details}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Block-based Agentic Pipeline System")
    parser.add_argument("input_file", help="Path to the input JSON file")
    parser.add_argument("--output", "-o", help="Path to the output JSON file")
    parser.add_argument("--config", "-c", help="Path to the configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Run the pipeline
    run_pipeline(
        input_file=args.input_file,
        output_file=args.output,
        config_file=args.config,
        verbose=args.verbose,
    )