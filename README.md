# Block-Based Agentic Pipeline System

A modular, block-based system for creating and executing automated workflows with minimal dependencies, designed for business users.

## Overview

This system enables users to create complex data processing and automation pipelines using a block-based approach. Each block represents a specific functionality that can be connected to form end-to-end workflows. The system takes structured JSON input describing the pipeline configuration and executes the defined workflow with real-time progress streaming.

## Features

- **Modular Architecture**: Easily composable and extensible block system
- **Low Dependencies**: Minimal external packages required
- **Real-time Streaming**: Live results and logs to frontend applications
- **Block Library**: Ready-to-use blocks for common operations
- **Error Handling**: Robust error tracking and reporting
- **Extensibility**: Simple framework for adding custom blocks
- **Multi-Provider LLM Support**: Flexible client manager for different LLM providers
- **Configuration Management**: Centralized configuration with environment variable support

## Block Types

The system includes the following block types:

- **Text Box**: Text input with formatting options
- **Input File**: File upload and parsing (various formats)
- **Scripting**: Python and C script execution
- **Output Generator**: Content formatting to Markdown, DOCX, and CSS
- **LLM**: Language model integration
- **JSON Schema**: JSON validation and transformation
- **Pseudo-RAG**: Retrieval-augmented generation
  - **Chunker**: Text splitting into manageable chunks
  - **Slicer**: Chunk processing and organization
- **Repeater**: Iteration over collections

## Getting Started

### Option 1: Using VS Code Devcontainer (Recommended)

The easiest way to spin up this project is using VS Code Devcontainers:

1. Prerequisites:
   - Install [Docker](https://www.docker.com/products/docker-desktop)
   - Install [VS Code](https://code.visualstudio.com/)
   - Install the [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension

2. Open the project in VS Code:
   ```bash
   git clone https://github.com/yourusername/block-agent-backend.git
   cd block-agent-backend
   code .
   ```

3. When prompted "Reopen in Container" or press F1 and select "Remote-Containers: Reopen in Container"

4. The container will build and install all dependencies automatically

5. Set up your environment variables:
   - Create a `.env` file in the root directory with your API keys:
   ```
   BLOCK_AGENTS_LLM_PROVIDERS_OPENAI_API_KEY=your-openai-key
   BLOCK_AGENTS_LLM_PROVIDERS_ANTHROPIC_API_KEY=your-anthropic-key
   ```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/block-agent-backend.git
cd block-agent-backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the project in development mode
pip install -e .
```

### Command Line Usage

You can run pipelines directly from the command line:

```bash
# Run a pipeline with an input file
python -m block_agents input_file.json

# Specify an output file
python -m block_agents input_file.json --output results.json

# Enable verbose logging
python -m block_agents input_file.json --verbose
```

The input JSON file should contain both the pipeline definition and input values.

### API Usage

1. Define a pipeline configuration:

```json
{
  "pipeline_id": "simple_pipeline",
  "name": "Simple Text Processing",
  "description": "A basic pipeline to process text with an LLM",
  "blocks": [
    {
      "id": "input",
      "type": "text_input",
      "config": {
        "default_text": "Enter your text here"
      },
      "next": ["llm_process"]
    },
    {
      "id": "llm_process",
      "type": "llm",
      "config": {
        "model": "default_model",
        "temperature": 0.7
      },
      "next": ["output"]
    },
    {
      "id": "output",
      "type": "output_generator",
      "config": {
        "format": "markdown"
      },
      "next": []
    }
  ],
  "output": "output"
}
```

2. Execute the pipeline:

```python
from block_agents.core.pipeline import Pipeline
from block_agents.core.config import Config
import json

# Load the pipeline definition
with open("pipeline_definition.json", "r") as f:
    pipeline_def = json.load(f)

# Create config and pipeline instance
config = Config.load()
pipeline = Pipeline(pipeline_def, config)

# Run with input values
result = pipeline.execute({
    "input": {
        "text": "Analyze the market trends for renewable energy"
    }
})

print(result)
```

3. Stream results (for frontend integration):

```python
# Add a streaming subscriber
def handle_stream_event(event):
    event_type = event.event_type
    block_id = event.block_id
    data = event.data
    
    print(f"Event: {event_type} from {block_id}")
    if event_type == "block_progress" and block_id == "llm_process":
        print(f"Partial result: {data.get('partial_result')}")

# Execute with streaming
pipeline.add_subscriber(handle_stream_event)
pipeline.execute_async(input_values)
```

### API Server Usage

To start the API server:

```bash
# Start the API server on port 8080
python -m block_agents.main
```

You can then interact with the API using tools like `curl`, `httpie`, or any HTTP client:

```bash
# Execute a pipeline
curl -X POST http://localhost:8080/api/pipelines/execute \
  -H "Content-Type: application/json" \
  -d @block_agents/examples/input_values.json

# Stream pipeline events
curl -N http://localhost:8080/api/pipelines/{execution_id}/stream
```

### Configuring API Keys

This project requires API keys for LLM providers. You can set them up in several ways:

1. Environment variables:
```bash
export BLOCK_AGENTS_LLM_PROVIDERS_OPENAI_API_KEY=your-openai-key
export BLOCK_AGENTS_LLM_PROVIDERS_ANTHROPIC_API_KEY=your-anthropic-key
```

2. `.env` file in the project root (recommended for development):
```
BLOCK_AGENTS_LLM_PROVIDERS_OPENAI_API_KEY=your-openai-key
BLOCK_AGENTS_LLM_PROVIDERS_ANTHROPIC_API_KEY=your-anthropic-key
```

3. Configuration file (`config.yaml`):
```yaml
block_agents:
  llm:
    providers:
      openai:
        api_key: "your-openai-key"
      anthropic:
        api_key: "your-anthropic-key"
```

## Pipeline Definition Structure

```json
{
  "pipeline_id": "unique_pipeline_identifier",
  "name": "Human-readable pipeline name",
  "description": "Pipeline description",
  "stream_config": {
    "enabled": true,
    "log_level": "info",
    "include_block_types": ["llm", "rag", "script"],
    "throttle_ms": 100
  },
  "blocks": [
    {
      "id": "block_1",
      "type": "text_input",
      "config": { ... },
      "next": ["block_2"]
    },
    {
      "id": "block_2",
      "type": "llm",
      "config": { ... },
      "next": ["block_3"]
    }
    // Additional blocks
  ],
  "output": "block_id_of_final_output"
}
```

## Input Format

```json
{
  "pipeline_id": "example_pipeline",
  "input_values": {
    "block_1": {
      "text": "Sample input text"
    },
    "global_parameters": {
      "user_id": "user123"
    }
  }
}
```

## Project Structure

```
block_agents/
├── __init__.py
├── __main__.py            # Command-line interface
├── core/
│   ├── __init__.py
│   ├── pipeline.py        # Pipeline execution engine
│   ├── block.py           # Base Block class
│   ├── context.py         # Context management
│   ├── stream.py          # Streaming functionality
│   └── errors.py          # Error handling
├── blocks/
│   ├── __init__.py
│   ├── text.py            # Text-related blocks
│   ├── file.py            # File handling blocks
│   ├── script.py          # Script execution blocks
│   ├── output.py          # Output generation blocks
│   ├── llm.py             # LLM integration blocks
│   ├── llm_providers/     # LLM provider implementations
│   ├── json_schema.py     # JSON Schema blocks
│   ├── rag.py             # RAG-related blocks
│   └── repeater.py        # Iteration blocks
├── utils/
│   ├── __init__.py
│   ├── validators.py      # Input validation utilities
│   └── helpers.py         # Helper functions
├── api/
│   ├── __init__.py
│   ├── routes.py          # API endpoint definitions
│   └── stream.py          # Streaming endpoint handlers
├── tests/
│   ├── __init__.py
│   ├── test_blocks/       # Tests for individual blocks
│   ├── test_pipeline.py   # Pipeline execution tests
│   └── test_stream.py     # Streaming tests
├── examples/
│   ├── simple_pipeline.json
│   ├── llm_processing.json
│   └── rag_pipeline.json
├── main.py                # Application entry point
├── requirements.txt       # Dependencies
└── README.md              # This file
```

## Creating Custom Blocks

1. Create a new Python file in the `blocks` directory
2. Define a class inheriting from the base `Block` class
3. Implement the `process` method

```python
from src.core.block import Block

class CustomBlock(Block):
    def __init__(self, block_id, config):
        super().__init__(block_id, config)
        # Initialize any specific properties
        
    def process(self, inputs, context):
        # Get stream manager for progress updates
        stream = context.get_stream_manager()
        
        # Emit start event
        stream.emit("block_start", self.id, {"message": "Starting custom processing"})
        
        # Your processing logic here
        result = self._your_processing_function(inputs)
        
        # Emit completion event
        stream.emit("block_complete", self.id, {"result": result})
        
        return result
```

4. Register your block in the block registry:

```python
from src.core.registry import BlockRegistry
from .custom_block import CustomBlock

BlockRegistry.register("custom_block_type", CustomBlock)
```

## API Integration

### Starting a Pipeline

```http
POST /api/pipelines/execute
Content-Type: application/json

{
  "pipeline_id": "example_pipeline",
  "input_values": {
    "block_1": {
      "text": "Sample input text"
    }
  }
}
```

### Streaming Results

```http
GET /api/pipelines/{pipeline_id}/stream
```

Response is a server-sent event stream:

```
event: block_start
data: {"pipeline_id": "example_pipeline", "block_id": "block_1", "timestamp": 1646870400, "data": {"message": "Starting processing"}}

event: block_progress
data: {"pipeline_id": "example_pipeline", "block_id": "llm_block", "timestamp": 1646870401, "data": {"progress": 0.5, "partial_result": "The analysis indicates"}}

event: block_complete
data: {"pipeline_id": "example_pipeline", "block_id": "llm_block", "timestamp": 1646870402, "data": {"result": "The analysis indicates that renewable energy..."}}
```

## Configuration Management

The system uses a centralized configuration approach that supports multiple sources:

### Configuration Sources (in order of precedence)

1. Command-line arguments
2. Environment variables
3. Configuration file (`config.yaml` or `config.json`)
4. Default values

### Required Configurations

```yaml
# config.yaml example
block_agents:
  # General settings
  log_level: "info"  # debug, info, warning, error
  max_pipeline_runtime_seconds: 3600
  temp_directory: "/tmp/block_agents"
  
  # LLM Provider settings
  llm:
    default_provider: "openai"  # Default provider to use
    providers:
      openai:
        api_key: "${OPENAI_API_KEY}"  # Environment variable reference
        default_model: "gpt-4"
        timeout_seconds: 60
      anthropic:
        api_key: "${ANTHROPIC_API_KEY}"
        default_model: "claude-3-opus"
        timeout_seconds: 120
      cohere:
        api_key: "${COHERE_API_KEY}"
        default_model: "command-r"
        timeout_seconds: 30
      local:
        endpoint: "http://localhost:8000/v1"
        default_model: "local-model"
  
  # Storage settings
  storage:
    type: "filesystem"  # filesystem, s3, database
    path: "./data"
    
  # API server settings
  api:
    host: "0.0.0.0"
    port: 8080
    cors_origins: ["http://localhost:3000"]
    
  # Streaming settings
  streaming:
    enabled: true
    buffer_size: 1024
    max_clients: 100
```

### Environment Variables

All configuration values can be overridden with environment variables using the prefix `BLOCK_AGENTS_`:

```bash
# Example environment variables
export BLOCK_AGENTS_LOG_LEVEL=debug
export BLOCK_AGENTS_LLM_DEFAULT_PROVIDER=anthropic
export BLOCK_AGENTS_LLM_PROVIDERS_OPENAI_API_KEY=your-api-key-here
```

### Loading Configuration

```python
from block_agents.core.config import Config

# Load from default locations
config = Config.load()

# Specify a config file
config = Config.load("path/to/custom/config.yaml")

# Access configuration values
log_level = config.get("log_level")
openai_api_key = config.get("llm.providers.openai.api_key")
```

## LLM Client Manager

The system includes a client manager to handle different LLM providers with a unified interface.

### Supported Providers

- OpenAI (GPT models)
- Anthropic (Claude models)
- Cohere
- Hugging Face
- Local models (via API endpoints)

### Usage in Blocks

```python
from block_agents.core.client_manager import LLMClientManager

class LLMBlock(Block):
    def process(self, inputs, context):
        # Get LLM client manager
        client_manager = context.get_client_manager()
        
        # Get client for specified provider (or default if not specified)
        provider = self.config.get("provider", None)
        client = client_manager.get_client(provider)
        
        # Use the client with standardized interface
        response = client.generate(
            prompt=inputs["prompt"],
            max_tokens=self.config.get("max_tokens", 1000),
            temperature=self.config.get("temperature", 0.7)
        )
        
        return {"generated_text": response.text}
```

### Adding a Custom Provider

```python
from block_agents.core.client_manager import BaseLLMClient, register_provider

class CustomProviderClient(BaseLLMClient):
    def __init__(self, config):
        super().__init__(config)
        # Initialize your client
        
    def generate(self, prompt, **kwargs):
        # Implement generation logic
        pass
        
    def stream_generate(self, prompt, callback, **kwargs):
        # Implement streaming generation
        pass

# Register the provider
register_provider("custom_provider", CustomProviderClient)
```