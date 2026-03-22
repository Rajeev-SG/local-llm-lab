#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./lib.sh
source "${ROOT_DIR}/scripts/lib.sh"

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}"
    exit 1
  fi
}

require_cmd curl
require_cmd jq

PORT="$(preferred_openwebui_port)"
OPENWEBUI_URL="${OPENWEBUI_URL:-http://localhost:${PORT}}"
OPENWEBUI_EMAIL="${OPENWEBUI_EMAIL:-rajeev.sgill@gmail.com}"
OPENWEBUI_PASSWORD="${OPENWEBUI_PASSWORD:-}"
OPENWEBUI_TOKEN="${OPENWEBUI_TOKEN:-}"

if ! curl -fsS "${OPENWEBUI_URL}/api/config" >/dev/null 2>&1; then
  echo "Open WebUI is not responding at ${OPENWEBUI_URL}"
  echo "Start it first with ${ROOT_DIR}/scripts/start-openwebui.sh"
  exit 1
fi

if ! curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Ollama is not running at ${OLLAMA_HOST}"
  echo "Start it first with ${ROOT_DIR}/scripts/start-ollama.sh"
  exit 1
fi

if [[ -z "${OPENWEBUI_TOKEN}" ]]; then
  if [[ -z "${OPENWEBUI_PASSWORD}" ]]; then
    echo "Set OPENWEBUI_PASSWORD or OPENWEBUI_TOKEN before running this script."
    exit 1
  fi

  OPENWEBUI_TOKEN="$(
    curl -fsS "${OPENWEBUI_URL}/api/v1/auths/signin" \
      -H 'Content-Type: application/json' \
      -d "$(jq -cn --arg email "${OPENWEBUI_EMAIL}" --arg password "${OPENWEBUI_PASSWORD}" '{email:$email,password:$password}')" \
      | jq -r '.token'
  )"
fi

api() {
  local method="$1"
  local path="$2"
  local payload="${3:-}"

  if [[ -n "${payload}" ]]; then
    curl -fsS -X "${method}" "${OPENWEBUI_URL}${path}" \
      -H "Authorization: Bearer ${OPENWEBUI_TOKEN}" \
      -H 'Content-Type: application/json' \
      -d "${payload}"
  else
    curl -fsS -X "${method}" "${OPENWEBUI_URL}${path}" \
      -H "Authorization: Bearer ${OPENWEBUI_TOKEN}"
  fi
}

MODELS_JSON="$(api GET /api/v1/models/export)"

upsert_model() {
  local id="$1"
  local payload="$2"

  if jq -e --arg id "${id}" '.[] | select(.id == $id)' >/dev/null <<< "${MODELS_JSON}"; then
    api POST /api/v1/models/model/update "${payload}" >/dev/null
    echo "  updated ${id}"
  else
    api POST /api/v1/models/create "${payload}" >/dev/null
    echo "  created ${id}"
  fi
}

delete_if_present() {
  local id="$1"
  if jq -e --arg id "${id}" '.[] | select(.id == $id)' >/dev/null <<< "${MODELS_JSON}"; then
    api POST /api/v1/models/model/delete "$(jq -cn --arg id "${id}" '{id:$id}')" >/dev/null
    echo "  deleted ${id}"
  fi
}

echo "Syncing Open WebUI role presets at ${OPENWEBUI_URL}..."

delete_if_present "local-helper-fast-ui"
delete_if_present "owui-local-helper-fast"
delete_if_present "owui-local-helper-safe"
delete_if_present "owui-local-helper-heavy"
delete_if_present "owui-local-coder-helper"
delete_if_present "owui-local-thinker-clean"
delete_if_present "owui-local-reasoner-clean"

upsert_model "local-helper-fast:latest" "$(
  jq -cn '
    {
      id: "local-helper-fast:latest",
      base_model_id: "qwen3.5:9b",
      name: "Local Helper Fast",
      meta: {
        description: "Fast local helper with Qwen 3.5 thinking disabled for clean chat output.",
        tags: [{name:"local"}, {name:"helper"}, {name:"fast"}]
      },
      params: {
        system: "You are local-helper-fast, a deterministic context compressor. Return only the requested answer format. Never reveal hidden reasoning. If the request asks for JSON, return only valid JSON.",
        temperature: 0,
        top_p: 0.2,
        num_ctx: 32768,
        think: false
      },
      access_grants: [],
      is_active: true
    }'
)"

upsert_model "local-helper-safe:latest" "$(
  jq -cn '
    {
      id: "local-helper-safe:latest",
      base_model_id: "phi4:latest",
      name: "Local Helper Safe",
      meta: {
        description: "Conservative checklist-style helper for summaries, triage, and low-risk extraction.",
        tags: [{name:"local"}, {name:"helper"}, {name:"safe"}]
      },
      params: {
        system: "You are local-helper-safe, a conservative checklist-style summarizer. Return only the requested answer format. Prefer explicit unknowns over guesses. Never reveal hidden reasoning.",
        temperature: 0,
        top_p: 0.2,
        num_ctx: 32768
      },
      access_grants: [],
      is_active: true
    }'
)"

upsert_model "local-helper-heavy:latest" "$(
  jq -cn '
    {
      id: "local-helper-heavy:latest",
      base_model_id: "mistral-small:22b",
      name: "Local Helper Heavy",
      meta: {
        description: "Heavier local synthesis model for harder distillation tasks.",
        tags: [{name:"local"}, {name:"helper"}, {name:"heavy"}]
      },
      params: {
        system: "You are local-helper-heavy, a code-aware distillation model for difficult local compression tasks. Return only the requested answer format. Do not expose chain-of-thought or scratch work.",
        temperature: 0.1,
        top_p: 0.2,
        num_ctx: 32768
      },
      access_grants: [],
      is_active: true
    }'
)"

upsert_model "local-coder-helper:latest" "$(
  jq -cn '
    {
      id: "local-coder-helper:latest",
      base_model_id: "qwen2.5-coder:14b",
      name: "Local Coder Helper",
      meta: {
        description: "Code-aware helper for API surfaces, diffs, and contract extraction.",
        tags: [{name:"local"}, {name:"coder"}]
      },
      params: {
        system: "You are local-coder-helper. Produce compact, code-aware answers for APIs, diffs, contracts, and repo slices. Never reveal hidden reasoning. Prefer bullets or valid JSON when asked.",
        temperature: 0,
        top_p: 0.2,
        num_ctx: 32768
      },
      access_grants: [],
      is_active: true
    }'
)"

upsert_model "local-thinker-clean:latest" "$(
  jq -cn '
    {
      id: "local-thinker-clean:latest",
      base_model_id: "qwen2.5:14b",
      name: "Local Thinker Clean",
      meta: {
        description: "Clean synthesis model for broader local analysis without visible reasoning traces.",
        tags: [{name:"local"}, {name:"thinker"}]
      },
      params: {
        system: "You are local-thinker-clean. Synthesize the answer and return only the final result unless the user explicitly asks for detailed reasoning. Never expose hidden reasoning or scratch work.",
        temperature: 0.1,
        top_p: 0.2,
        num_ctx: 32768
      },
      access_grants: [],
      is_active: true
    }'
)"

upsert_model "local-reasoner-clean:latest" "$(
  jq -cn '
    {
      id: "local-reasoner-clean:latest",
      base_model_id: "gpt-oss:20b",
      name: "Local Reasoner Clean",
      meta: {
        description: "Optional deeper-reasoning preset with GPT-OSS effort reduced for cleaner Open WebUI output.",
        tags: [{name:"local"}, {name:"reasoner"}]
      },
      params: {
        system: "You are local-reasoner-clean. Give the final answer first. Keep any reasoning minimal and useful. Obey exact-output requests literally and never dump raw scratch notes.",
        temperature: 0.1,
        top_p: 0.2,
        num_ctx: 32768,
        think: "low"
      },
      access_grants: [],
      is_active: true
    }'
)"

echo ""
echo "Open WebUI role presets are ready."
echo "Browse to ${OPENWEBUI_URL} and select one of:"
echo "  - local-helper-fast:latest"
echo "  - local-helper-safe:latest"
echo "  - local-helper-heavy:latest"
echo "  - local-coder-helper:latest"
echo "  - local-thinker-clean:latest"
echo "  - local-reasoner-clean:latest"
