#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib.sh"
COMPOSE=(docker compose -f "${ROOT_DIR}/compose.openwebui.yaml")
if [[ -f "${ROOT_DIR}/.env.local" ]]; then COMPOSE+=(--env-file "${ROOT_DIR}/.env.local"); fi
fail=0
check() { if "$@"; then echo "PASS $*"; else echo "FAIL $*"; fail=1; fi; }

check command -v docker
check docker info
check test -f "${ROOT_DIR}/config/bridge-allowlist.json"
check jq empty "${ROOT_DIR}/config/bridge-allowlist.json"
check "${COMPOSE[@]}" config --quiet
image="$("${COMPOSE[@]}" config --format json | jq -r '.services["open-webui"].image')"
if [[ "${image}" =~ :main$|:latest$ ]]; then echo "FAIL mutable image ${image}"; fail=1; else echo "PASS pinned image ${image}"; fi
terminal_image="$("${COMPOSE[@]}" config --format json | jq -r '.services["open-terminal"].image')"
if [[ "${terminal_image}" =~ :main$|:latest$ ]]; then echo "FAIL mutable terminal image ${terminal_image}"; fail=1; else echo "PASS pinned terminal image ${terminal_image}"; fi
if docker_container_running open-terminal-lab && docker exec open-terminal-lab curl -fsS http://localhost:8000/health >/dev/null; then
  echo "PASS Open Terminal reachable"
else
  echo "WARN Open Terminal not reachable"
fi
if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then echo "PASS OpenRouter key supplied via environment"; else echo "INFO OpenRouter key absent; cloud checks skipped"; fi
if curl -fsS "${OLLAMA_HOST:-http://localhost:11434}/api/tags" >/dev/null 2>&1; then echo "PASS Ollama reachable"; else echo "WARN Ollama not reachable"; fi
exit "${fail}"
