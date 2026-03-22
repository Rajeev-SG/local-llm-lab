#!/bin/bash
set -euo pipefail

MODEL="${1:-mistral-small:22b}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}"
OUTPUT_FILE="${OUTPUT_DIR}/benchmark-results.md"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✗ Ollama is not running. Run: ${ROOT_DIR}/scripts/start-ollama.sh"
    exit 1
fi

echo "=== Benchmarking ${MODEL} ==="

# Test prompt
PROMPT="Write a short poem about programming."

# Run benchmark
echo "Running benchmark prompt..."
START_TIME=$(date +%s.%N)
OUTPUT=$(ollama run "${MODEL}" -- "${PROMPT}" 2>&1)
END_TIME=$(date +%s.%N)

ELAPSED=$(echo "${END_TIME} - ${START_TIME}" | bc)

# Count tokens (rough estimate: ~4 chars per token)
TOKEN_COUNT=$(echo "${OUTPUT}" | wc -c | tr -d ' ')
TOKENS=$(echo "scale=0; ${TOKEN_COUNT} / 4" | bc)

if [ "$(echo "${ELAPSED} > 0" | bc)" -eq 1 ] && [ "${TOKENS}" -gt 0 ]; then
    TPS=$(echo "scale=2; ${TOKENS} / ${ELAPSED}" | bc)
else
    TPS="0"
fi

# Get model size
MODEL_SIZE=$(ollama list | grep "${MODEL%%:*}" | awk '{print $3}' || echo "unknown")

# Write results
{
    echo "# Benchmark Results"
    echo ""
    echo "**Date:** $(date)"
    echo "**Model:** ${MODEL}"
    echo "**Size:** ${MODEL_SIZE}"
    echo ""
    echo "## Metrics"
    echo ""
    echo "| Metric | Value |"
    echo "|--------|-------|"
    echo "| Elapsed Time | ${ELAPSED}s |"
    echo "| Est. Tokens | ${TOKENS} |"
    echo "| Est. Tokens/sec | ${TPS} |"
    echo ""
    echo "## Output"
    echo ""
    echo '```'
    echo "${OUTPUT}"
    echo '```'
} > "${OUTPUT_FILE}"

echo ""
echo "Results written to: ${OUTPUT_FILE}"
cat "${OUTPUT_FILE}"
