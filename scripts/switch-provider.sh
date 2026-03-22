#!/usr/bin/env bash
# Quick switch between cc-mirror providers
# Usage: switch-provider.sh [openrouter|qwen3|coder|deepseek|72b]

set -euo pipefail

PROVIDER="${1:-}"

if [[ -z "$PROVIDER" ]]; then
    echo "Available providers:"
    echo ""
    echo "  openrouter  → cc-openrouter (current recommended cloud path)"
    echo "  qwen3       → cc-ollama-qwen3 (legacy local 30b profile)"
    echo "  coder       → cc-ollama-coder (legacy local 30b coding profile)"
    echo "  deepseek    → cc-ollama-deepseek (legacy local 32b reasoning profile)"
    echo "  72b         → cc-ollama-72b (legacy local 72b heavy profile)"
    echo ""
    echo "Usage: switch-provider.sh <provider>"
    echo "Example: switch-provider.sh coder"
    exit 0
fi

case "$PROVIDER" in
    openrouter|or)
        CMD="cc-openrouter"
        DESC="OpenRouter (current recommended cloud path)"
        ;;
    qwen3|q3)
        CMD="cc-ollama-qwen3"
        DESC="Ollama qwen3:30b (legacy local profile)"
        ;;
    coder|c)
        CMD="cc-ollama-coder"
        DESC="Ollama qwen3-coder:30b (legacy local coding profile)"
        ;;
    deepseek|ds|r1)
        CMD="cc-ollama-deepseek"
        DESC="Ollama deepseek-r1:32b (legacy local reasoning profile)"
        ;;
    72b|large)
        CMD="cc-ollama-72b"
        DESC="Ollama qwen2.5:72b (legacy local heavy profile)"
        ;;
    *)
        echo "Unknown provider: $PROVIDER"
        exit 1
        ;;
esac

# Check if variant exists
if ! command -v "$CMD" &> /dev/null; then
    echo "✗ Variant '$CMD' not found"
    echo "  Run: ~/local-llm-lab/scripts/create-ollama-variants.sh"
    exit 1
fi

# For Ollama variants, ensure Ollama is running
if [[ "$CMD" == cc-ollama-* ]]; then
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Starting Ollama..."
        ~/local-llm-lab/scripts/start-ollama.sh
    fi
fi

echo "Switched to: $DESC"
echo "Running: $CMD"
echo ""
exec "$CMD" "$@"
