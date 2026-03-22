#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./lib.sh
source "${ROOT_DIR}/scripts/lib.sh"

if ! curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Ollama is not running at ${OLLAMA_HOST}"
  echo "Start it first with ${ROOT_DIR}/scripts/start-ollama.sh"
  exit 1
fi

ALIASES=(
  "local-helper-fast|modelfiles/local-helper-fast.Modelfile|qwen3.5:9b"
  "local-helper-safe|modelfiles/local-helper-safe.Modelfile|phi4:latest"
  "local-helper-heavy|modelfiles/local-helper-heavy.Modelfile|mistral-small:22b"
  "local-coder-helper|modelfiles/local-coder-helper.Modelfile|qwen2.5-coder:14b"
  "local-reasoner-clean|modelfiles/local-reasoner-clean.Modelfile|gpt-oss:20b"
  "local-thinker-clean|modelfiles/local-thinker-clean.Modelfile|qwen2.5:14b"
)

missing=0
for alias_def in "${ALIASES[@]}"; do
  IFS='|' read -r alias_name _ base_model <<< "${alias_def}"
  if ! ollama list | awk 'NR>1 {print $1}' | grep -Fxq "${base_model}"; then
    echo "Missing base model for ${alias_name}: ${base_model}"
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  echo ""
  echo "Pull the missing base models first, then rerun this script."
  exit 1
fi

echo "Creating role-tuned Ollama aliases..."
for alias_def in "${ALIASES[@]}"; do
  IFS='|' read -r alias_name modelfile_rel _ <<< "${alias_def}"
  modelfile_path="${ROOT_DIR}/${modelfile_rel}"
  echo "  -> ${alias_name}"
  ollama create "${alias_name}" -f "${modelfile_path}" >/dev/null
done

echo ""
echo "Alias setup complete."
echo "Note: thinking-capable bases such as qwen3.5 and gpt-oss still need client-level 'think' settings for the cleanest output."
echo "For Open WebUI, also run ${ROOT_DIR}/scripts/setup-openwebui-role-models.sh."
echo ""
ollama list | awk 'NR==1 || /^local-/' | sed 's/^/  /'
