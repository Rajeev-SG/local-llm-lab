#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/compose.openwebui.yaml"
COMPOSE=(docker compose -f "${COMPOSE_FILE}")
if [[ -f "${ROOT_DIR}/.env.local" ]]; then
  COMPOSE+=(--env-file "${ROOT_DIR}/.env.local")
fi
source "${ROOT_DIR}/scripts/lib.sh"

command -v docker >/dev/null || { echo "Missing docker" >&2; exit 1; }
command -v openssl >/dev/null || { echo "Missing openssl" >&2; exit 1; }

ensure_local_secret() {
  local key="$1"
  local current="${!key:-}"
  if [[ -n "${current}" ]]; then
    return
  fi
  if [[ -f "${ROOT_DIR}/.env.local" ]]; then
    current="$(awk -F= -v key="${key}" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "${ROOT_DIR}/.env.local")"
  fi
  if [[ -z "${current}" ]]; then
    umask 077
    touch "${ROOT_DIR}/.env.local"
    current="$(openssl rand -hex 32)"
    if grep -q "^${key}=" "${ROOT_DIR}/.env.local"; then
      local temporary
      temporary="$(mktemp "${ROOT_DIR}/.env.local.XXXXXX")"
      awk -F= -v key="${key}" -v value="${current}" '
        $1 == key && !replaced { print key "=" value; replaced=1; next }
        $1 == key { next }
        { print }
      ' "${ROOT_DIR}/.env.local" > "${temporary}"
      mv "${temporary}" "${ROOT_DIR}/.env.local"
    else
      printf '%s=%s\n' "${key}" "${current}" >> "${ROOT_DIR}/.env.local"
    fi
    chmod 600 "${ROOT_DIR}/.env.local"
    echo "Generated ${key} in ignored .env.local"
  fi
  export "${key}=${current}"
}

ensure_local_secret WEBUI_SECRET_KEY
ensure_local_secret OPEN_TERMINAL_API_KEY

if [[ -z "${OPENROUTER_API_KEY:-}" && -f "${OPENROUTER_ENV_FILE:-${HOME}/.config/claude-openrouter/env.sh}" ]]; then
  OPENROUTER_API_KEY="$(awk -F= '
    /^(export )?(OPENROUTER_API_KEY|ANTHROPIC_AUTH_TOKEN)=/ {
      sub(/^(export )?[^=]*=/, "")
      gsub(/^['\"']|['\"']$/, "")
      print
      exit
    }
  ' "${OPENROUTER_ENV_FILE:-${HOME}/.config/claude-openrouter/env.sh}")"
  export OPENROUTER_API_KEY
fi

export OPENWEBUI_PORT="${OPENWEBUI_PORT:-$(preferred_openwebui_port)}"
export OPENWEBUI_VOLUME_NAME="${OPENWEBUI_VOLUME_NAME:-open-webui-data}"
export OPENWEBUI_CONTAINER_NAME="${OPENWEBUI_CONTAINER_NAME:-open-webui-lab}"
export OPENWEBUI_IMAGE="${OPENWEBUI_IMAGE:-ghcr.io/open-webui/open-webui@sha256:6bb1fbe8ab0a3e0456067f493044ffb66a30a65a34be47f6a5862176a370dd16}"

if [[ "${OPENWEBUI_IMAGE}" =~ :main$|:latest$ ]]; then
  echo "Refusing mutable Open WebUI image: ${OPENWEBUI_IMAGE}" >&2
  echo "Use a version tag or digest explicitly." >&2
  exit 1
fi

if [[ -n "${OPENROUTER_API_KEY:-}" && -z "${OPENAI_API_KEYS:-}" ]]; then
  export OPENAI_API_KEYS="${OPENROUTER_API_KEY}"
fi

# Remove only the named container. Its named volume is deliberately preserved.
if docker_container_exists "${OPENWEBUI_CONTAINER_NAME}"; then
  current_image="$(docker inspect --format '{{.Config.Image}}' "${OPENWEBUI_CONTAINER_NAME}")"
  if [[ "${current_image}" != "${OPENWEBUI_IMAGE}" ]]; then
    echo "Recreating ${OPENWEBUI_CONTAINER_NAME}: ${current_image} -> ${OPENWEBUI_IMAGE}"
    docker rm -f "${OPENWEBUI_CONTAINER_NAME}" >/dev/null
  fi
fi

"${COMPOSE[@]}" config >/dev/null
"${COMPOSE[@]}" pull open-webui open-terminal
"${COMPOSE[@]}" up -d --no-build open-terminal open-webui
save_openwebui_port "${OPENWEBUI_PORT}"
echo "Open WebUI is available at http://localhost:${OPENWEBUI_PORT}"
echo "Persistent volume preserved: ${OPENWEBUI_VOLUME_NAME}"
echo "Isolated terminal available inside the Compose network at http://open-terminal:8000"
