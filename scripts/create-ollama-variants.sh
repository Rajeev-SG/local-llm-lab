#!/usr/bin/env bash
set -euo pipefail

# Create cc-mirror Ollama variants for each model
# This integrates your local Ollama models with cc-mirror

echo "=== Creating CC-Mirror Ollama Variants ==="
echo ""

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✗ Ollama is not running. Starting it..."
    ~/local-llm-lab/scripts/start-ollama.sh
fi

# Variant definitions: name, sonnet_model, opus_model, haiku_model
VARIANTS=(
    "cc-ollama-qwen3:qwen3:30b:qwen3:30b:qwen3:30b"
    "cc-ollama-coder:qwen3-coder:30b:qwen3-coder:30b:qwen3-coder:30b"
    "cc-ollama-deepseek:deepseek-r1:32b:deepseek-r1:32b:deepseek-r1:32b"
    "cc-ollama-72b:qwen2.5:72b:qwen2.5:72b:qwen2.5:72b"
)

for variant_def in "${VARIANTS[@]}"; do
    IFS=':' read -r name sonnet opus haiku <<< "$variant_def"

    if [[ -d ~/.cc-mirror/"$name" ]]; then
        echo "  ○ $name already exists, skipping"
    else
        echo "  Creating $name..."
        npx cc-mirror quick --provider ollama \
            --name "$name" \
            --api-key "ollama" \
            --model-sonnet "$sonnet" \
            --model-opus "$opus" \
            --model-haiku "$haiku" \
            --brand ollama \
            --no-prompt-pack
    fi
done

echo ""
echo "=== Variants Created ==="
npx cc-mirror list

echo ""
echo "=== Usage ==="
echo "  cc-openrouter        # OpenRouter (cloud models)"
echo "  cc-ollama-qwen3      # Local qwen3:30b"
echo "  cc-ollama-coder      # Local qwen3-coder:30b"
echo "  cc-ollama-deepseek   # Local deepseek-r1:32b"
echo "  cc-ollama-72b        # Local qwen2.5:72b (large)"
