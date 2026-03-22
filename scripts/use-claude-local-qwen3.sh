#!/bin/bash
set -euo pipefail

# Claude Code wrapper for qwen3:30b
# Uses Ollama's Anthropic-compatible API

export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL="http://localhost:11434"

echo "Starting Claude Code with qwen3:30b (local via Ollama)"
echo "API endpoint: ${ANTHROPIC_BASE_URL}"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✗ Ollama is not running. Starting it..."
    ~/local-llm-lab/scripts/start-ollama.sh
fi

# Run Claude Code with the local model
claude --model qwen3:30b "$@"
