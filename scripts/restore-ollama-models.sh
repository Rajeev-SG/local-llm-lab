#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTORY="${ROOT_DIR}/output/inventory/current-models.json"
source "${ROOT_DIR}/scripts/lib.sh"

[[ -f "${INVENTORY}" ]] || { echo "Missing inventory: ${INVENTORY}" >&2; exit 1; }
curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null || {
  echo "Ollama is not reachable at ${OLLAMA_HOST}; run start-ollama.sh first." >&2
  exit 1
}

models=()
while IFS= read -r model; do
  [[ -n "${model}" ]] && models+=("${model}")
done < <(jq -r '.installed_models[] | select(.runtime == "ollama") | .model_name' "${INVENTORY}" | sort -u)
[[ ${#models[@]} -gt 0 ]] || { echo "No Ollama models in ${INVENTORY}" >&2; exit 1; }
for model in "${models[@]}"; do
  echo "Restoring ${model}"
  ollama pull "${model}"
done
echo "Restored ${#models[@]} Ollama model(s)."
