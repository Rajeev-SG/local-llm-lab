#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./lib.sh
source "${ROOT_DIR}/scripts/lib.sh"

echo "=== Local LLM Test Suite ==="
echo ""

if ! curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Ollama is not running at ${OLLAMA_HOST}"
  echo "Start it first with ${ROOT_DIR}/scripts/start-ollama.sh"
  exit 1
fi

echo "✓ Ollama is running"
echo ""
echo "=== Installed Models ==="
ollama list
echo ""

echo "=== API Tests For Thinking-Capable Models ==="
curl -fsS "${OLLAMA_HOST}/api/chat" \
  -d '{"model":"qwen3.5:9b","messages":[{"role":"user","content":"Reply with exactly: FAST_HELPER_OK"}],"think":false,"stream":false}' \
  | jq '{model:.model,content:.message.content,thinking:.message.thinking}'
echo ""

curl -fsS "${OLLAMA_HOST}/api/chat" \
  -d '{"model":"gpt-oss:20b","messages":[{"role":"user","content":"Reply with exactly: CLEAN_REASONER_OK"}],"think":"low","stream":false}' \
  | jq '{model:.model,content:.message.content,thinking_present:(.message.thinking != null)}'
echo ""

MODELS=(
  "local-helper-safe:latest|Return exactly: SAFE_HELPER_OK"
  "local-helper-heavy:latest|Return exactly: HEAVY_HELPER_OK"
  "local-coder-helper:latest|Return exactly: CODER_HELPER_OK"
  "local-thinker-clean:latest|Return exactly: CLEAN_THINKER_OK"
  "mistral-small:22b|Reply with exactly: MISTRAL22 OK"
  "phi4:latest|Reply with exactly: PHI4 OK"
  "gemma3:12b|Reply with exactly: GEMMA12 OK"
  "qwen2.5:14b|Reply with exactly: QWEN14 OK"
  "qwen2.5-coder:14b|Reply with exactly: QWENCODER14 OK"
)

for entry in "${MODELS[@]}"; do
  IFS='|' read -r model prompt <<< "${entry}"
  echo "=== Testing ${model} ==="
  if ollama list | awk 'NR>1 {print $1}' | grep -Fxq "${model}"; then
    time ollama run "${model}" "${prompt}" 2>&1 | tail -5
  else
    echo "⚠ Model ${model} not installed"
  fi
  echo ""
done

echo "=== Test Complete ==="
