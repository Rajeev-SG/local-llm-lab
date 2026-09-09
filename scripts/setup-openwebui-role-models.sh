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
OPENWEBUI_LOCAL_NUM_CTX="${OPENWEBUI_LOCAL_NUM_CTX:-8192}"

if ! curl -fsS "${OPENWEBUI_URL}/api/config" >/dev/null 2>&1; then
  echo "Open WebUI is not responding at ${OPENWEBUI_URL}"
  exit 1
fi

if ! curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Ollama is not running at ${OLLAMA_HOST}"
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

# Get current models to see what to update vs create
MODELS_JSON="$(api GET /api/v1/models/export)"

upsert_model() {
  local id="$1"
  local payload="$2"

  # Open WebUI's export endpoint omits overrides for provider base models, so
  # it cannot reliably distinguish create from update. A duplicate create is
  # rejected without changing state; retrying as update makes this idempotent.
  if api POST /api/v1/models/create "${payload}" >/dev/null 2>&1; then
    echo "  created ${id}"
  else
    api POST /api/v1/models/model/update "${payload}" >/dev/null
    echo "  updated ${id}"
  fi
}

delete_if_present() {
  local id="$1"
  if jq -e --arg id "${id}" '.[] | select(.id == $id)' >/dev/null <<< "${MODELS_JSON}"; then
    api POST /api/v1/models/model/delete "$(jq -cn --arg id "${id}" '{id:$id}')" >/dev/null
    echo "  deleted ${id}"
  fi
}

# Memory detection
detect_runtime_mem_gb() {
  if [[ -n "${OLLAMA_MEMORY_GB:-}" ]]; then
    echo "${OLLAMA_MEMORY_GB}"
    return
  fi

  local runtime
  runtime=$(preferred_ollama_runtime)

  if [[ "${runtime}" == "docker" ]]; then
    local docker_mem
    docker_mem=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0)
    if [[ "${docker_mem}" -gt 0 ]]; then
      # Convert bytes to GB using awk to avoid bc
      awk -v bytes="${docker_mem}" 'BEGIN { printf "%.1f", bytes / 1000000000 }'
      return
    fi
  fi

  # Fallback to host memory
  local host_mem
  host_mem=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
  awk -v bytes="${host_mem}" 'BEGIN { printf "%.1f", bytes / 1000000000 }'
}

RUNTIME_MEM_GB=$(detect_runtime_mem_gb)
echo "Detected Ollama runtime memory: ${RUNTIME_MEM_GB} GB"

ROLES_JSON='{
  "llama3.2:3b-cpu": {
    "name": "Llama 3.2 3B CPU",
    "description": "CPU-only fallback for reliable local Open WebUI testing.",
    "tags": ["local", "fallback", "cpu"]
  },
  "local-helper-fast": {
    "name": "Helper Fast",
    "description": "Fast local helper with Qwen 3.5 thinking disabled for clean chat output.",
    "tags": ["local", "helper", "fast"],
    "system": "You are local-helper-fast, a deterministic context compressor. Return only the requested answer format. Never reveal hidden reasoning. If the request asks for JSON, return only valid JSON.",
    "temperature": 0,
    "top_p": 0.2,
    "think": false
  },
  "local-helper-safe": {
    "name": "Helper Safe",
    "description": "Conservative checklist-style helper for summaries, triage, and low-risk extraction.",
    "tags": ["local", "helper", "safe"],
    "system": "You are local-helper-safe, a conservative checklist-style summarizer. Return only the requested answer format. Prefer explicit unknowns over guesses. Never reveal hidden reasoning.",
    "temperature": 0,
    "top_p": 0.2
  },
  "local-helper-heavy": {
    "name": "Helper Heavy",
    "description": "Heavier local synthesis model for harder distillation tasks.",
    "tags": ["local", "helper", "heavy"],
    "system": "You are local-helper-heavy, a code-aware distillation model for difficult local compression tasks. Return only the requested answer format. Do not expose chain-of-thought or scratch work.",
    "temperature": 0.1,
    "top_p": 0.2
  },
  "local-coder-helper": {
    "name": "Coder Helper",
    "description": "Code-aware helper for API surfaces, diffs, and contract extraction.",
    "tags": ["local", "coder"],
    "system": "You are local-coder-helper. Produce compact, code-aware answers for APIs, diffs, contracts, and repo slices. Never reveal hidden reasoning. Prefer bullets or valid JSON when asked.",
    "temperature": 0,
    "top_p": 0.2
  },
  "local-thinker-clean": {
    "name": "Thinker Clean",
    "description": "Clean synthesis model for broader local analysis without visible reasoning traces.",
    "tags": ["local", "thinker"],
    "system": "You are local-thinker-clean. Synthesize the answer and return only the final result unless the user explicitly asks for detailed reasoning. Never expose hidden reasoning or scratch work.",
    "temperature": 0.1,
    "top_p": 0.2
  },
  "local-reasoner-clean": {
    "name": "Reasoner Clean",
    "description": "Optional deeper-reasoning preset with GPT-OSS effort reduced for cleaner Open WebUI output.",
    "tags": ["local", "reasoner"],
    "system": "You are local-reasoner-clean. Give the final answer first. Keep any reasoning minimal and useful. Obey exact-output requests literally and never dump raw scratch notes.",
    "temperature": 0.1,
    "top_p": 0.2,
    "think": "low"
  }
}'

echo "Syncing Open WebUI model catalog..."

# Legacy deletions
delete_if_present "local-helper-fast-ui"
delete_if_present "owui-local-helper-fast"
delete_if_present "owui-local-helper-safe"
delete_if_present "owui-local-helper-heavy"
delete_if_present "owui-local-coder-helper"
delete_if_present "owui-local-thinker-clean"
delete_if_present "owui-local-reasoner-clean"

# Get live Ollama tags
OLLAMA_TAGS="$(curl -fsS "${OLLAMA_HOST}/api/tags")"

# Process models and generate upsert payloads
PAYLOADS=$(jq -c \
  --argjson ollama "${OLLAMA_TAGS}" \
  --argjson roles "${ROLES_JSON}" \
  --arg runtime_mem_gb "${RUNTIME_MEM_GB}" \
  --arg ctx_cap "${OPENWEBUI_LOCAL_NUM_CTX}" \
  '
  # Create a map of installed Ollama models from live tags
  ($ollama.models | map({key: .name, value: .size}) | from_entries) as $installed_sizes |

  .models | map(
    select(.runtime == "ollama") |
    select($installed_sizes[.model_name] != null) |
    . as $m |

    (($m.size_gb | tonumber) > ($runtime_mem_gb | tonumber * 0.7)) as $constrained |
    (if $m.context_tokens then [($m.context_tokens | tonumber), ($ctx_cap | tonumber)] | min else ($ctx_cap | tonumber) end) as $eff_ctx |

    # Base model record
    {
      id: $m.model_name,
      base_model_id: $m.model_name,
      name: ("Local LLM Lab — \($m.label) · \($m.parameters) · \($m.size_gb) GB" + (if $constrained then " · Needs more RAM" else "" end)),
      meta: {
        description: ($m.best_for + (if $constrained then " (Memory constrained on this runtime)" else "" end)),
        tags: (["local", "local-llm-lab", (if $constrained then "constrained" else "ready" end)] + ($m.capabilities // []) | unique | map({name: .}))
      },
      params: {
        num_ctx: $eff_ctx
      },
      access_grants: [],
      is_active: true
    },

    # Aliases
    (if $m.aliases then
      $m.aliases | map(
        . as $alias |
        ($alias | sub(":[Ll][Aa][Tt][Ee][Ss][Tt]$"; "")) as $alias_key |
        ($alias + (if ($alias | contains(":")) then "" else ":latest" end)) as $alias_id |
        ($roles[$alias_key] // {}) as $role |
        {
          id: $alias_id,
          # Customize the installed Ollama alias itself. Pointing at the
          # underlying weight model causes the provider raw alias entry to
          # shadow this friendly record in the Open WebUI model picker.
          base_model_id: $alias_id,
          name: ("Local LLM Lab — \($role.name // $alias_key) · \($m.parameters) · \($m.size_gb) GB" + (if $constrained then " · Needs more RAM" else "" end)),
          meta: {
            description: ($role.description // $m.best_for) + (if $constrained then " (Memory constrained on this runtime)" else "" end),
            tags: (["local", "local-llm-lab", (if $constrained then "constrained" else "ready" end)] + ($role.tags // ($m.capabilities // [])) | unique | map({name: .}))
          },
          params: ({
            system: ($role.system // ""),
            temperature: ($role.temperature // 0.8),
            top_p: ($role.top_p // 0.9),
            num_ctx: $eff_ctx
          } + (if $role.think != null then {think: $role.think} else {} end)),
          access_grants: [],
          is_active: true
        }
      )
    else
      empty
    end)
  ) | flatten | .[]
  ' "${ROOT_DIR}/config/model-guide-metadata.json"
)

while read -r payload; do
  [[ -z "${payload}" ]] && continue
  id=$(jq -r '.id' <<< "${payload}")
  upsert_model "${id}" "${payload}"
done <<< "${PAYLOADS}"

echo ""
echo "Open WebUI model catalog is ready."
