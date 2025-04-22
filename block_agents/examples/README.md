# Block Agent Pipeline Examples

This directory contains example pipeline definitions and input files for the block-based agentic pipeline system.

## Simple Pipeline

A basic pipeline to process text with an LLM:

```bash
# Run the simple pipeline with default input
python -m block_agents block_agents/examples/simple_pipeline.json

# Run with custom input values
python -m block_agents block_agents/examples/input_values.json

# Run with verbose output
python -m block_agents block_agents/examples/input_values.json --verbose

# Save output to a file
python -m block_agents block_agents/examples/input_values.json --output result.json
```

The simple pipeline consists of three blocks:
1. `input`: A text input block that provides a prompt
2. `llm_process`: An LLM block that processes the prompt
3. `output`: An output generator block that formats the LLM response

## API Usage

You can also run the pipelines through the API:

```bash
# Start the API server
python -m block_agents.main

# Then send requests to the API
curl -X POST http://localhost:8080/api/pipelines/execute \
  -H "Content-Type: application/json" \
  -d @block_agents/examples/input_values.json
```

The API provides endpoints for:
- Executing pipelines
- Monitoring pipeline execution status
- Getting pipeline results
- Streaming pipeline events in real-time