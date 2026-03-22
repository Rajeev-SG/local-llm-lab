#!/bin/bash
set -euo pipefail

# Claude Code wrapper for qwen2.5:72b
# Uses Ollama's Anthropic-compatible API
# Note: This is a large model - ensure you have sufficient RAM

export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL="http://localhost:11434"

echo "Starting Claude Code with qwen2.5:72b (local via Ollama)"
echo "API endpoint: ${ANTHROPIC_BASE_URL}"
echo "⚠ This is a 72B parameter model - requires significant RAM"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✗ Ollama is not running. Starting it..."
    ~/local-llm-lab/scripts/start-ollama.sh
fi

# Run Claude Code with the local model
claude --model qwen2.5:72b "$@"
