#!/bin/bash
set -e

# Get the project directory
PROJECT_DIR=$(pwd)
PROJECT_NAME=$(basename "$PROJECT_DIR")

echo "🚀 Setting up project: $PROJECT_NAME"

# Install project dependencies
if [ -f "pyproject.toml" ]; then
  echo "📦 Installing Python dependencies with UV..."
  uv pip install -e .
  
  # If there's a dev dependencies section
  if grep -q "\[dev-dependencies\]" pyproject.toml || grep -q "\[tool.poetry.dev-dependencies\]" pyproject.toml; then
    echo "📦 Installing dev dependencies..."
    uv pip install -e ".[dev]"
  fi
else
  echo "ℹ️ No pyproject.toml found, skipping dependency installation"
fi

# Set up pre-commit hooks if config exists
if [ -f ".pre-commit-config.yaml" ]; then
  echo "🔧 Setting up pre-commit hooks..."
  pre-commit install
fi

# Initialize git if not already done
if [ ! -d ".git" ]; then
  echo "🔧 Initializing git repository..."
  git init
  git config --local user.name "$(git config --global user.name || echo 'Your Name')"
  git config --local user.email "$(git config --global user.email || echo 'your.email@example.com')"
  
  # Add initial commit if the repository is new
  git add .
  git commit -m "Initial commit"
fi

echo "✅ Project setup complete!"
echo "To start developing, open your project in VS Code:"
echo "  code ."