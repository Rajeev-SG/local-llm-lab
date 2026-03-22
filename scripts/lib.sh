#!/bin/bash
set -euo pipefail

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENWEBUI_CONTAINER_NAME="${OPENWEBUI_CONTAINER_NAME:-open-webui-lab}"
OPENWEBUI_IMAGE="${OPENWEBUI_IMAGE:-ghcr.io/open-webui/open-webui:main}"
OPENWEBUI_VOLUME_NAME="${OPENWEBUI_VOLUME_NAME:-open-webui-data}"
OPENWEBUI_PORT_FILE="${LAB_ROOT}/.openwebui-port"
OPENWEBUI_INTERNAL_PORT="${OPENWEBUI_INTERNAL_PORT:-8080}"
OLLAMA_DOCKER_CONTAINER="${OLLAMA_DOCKER_CONTAINER:-ollama-lab}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

docker_container_exists() {
    local name="$1"
    docker ps -a --format '{{.Names}}' | grep -Fxq "${name}"
}

docker_container_running() {
    local name="$1"
    docker ps --format '{{.Names}}' | grep -Fxq "${name}"
}

is_port_listening() {
    local port="$1"
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
}

container_host_port() {
    local name="$1"
    local internal_port="$2"
    docker port "${name}" "${internal_port}/tcp" 2>/dev/null | head -n 1 | awk -F: '{print $NF}'
}

save_openwebui_port() {
    local port="$1"
    printf '%s\n' "${port}" > "${OPENWEBUI_PORT_FILE}"
}

preferred_openwebui_port() {
    if [[ -n "${OPENWEBUI_PORT:-}" ]]; then
        echo "${OPENWEBUI_PORT}"
        return
    fi

    if docker_container_exists "${OPENWEBUI_CONTAINER_NAME}"; then
        local existing_port
        existing_port="$(container_host_port "${OPENWEBUI_CONTAINER_NAME}" "${OPENWEBUI_INTERNAL_PORT}")"
        if [[ -n "${existing_port}" ]]; then
            echo "${existing_port}"
            return
        fi
    fi

    if [[ -f "${OPENWEBUI_PORT_FILE}" ]]; then
        local saved_port
        saved_port="$(tr -d '[:space:]' < "${OPENWEBUI_PORT_FILE}")"
        if [[ "${saved_port}" =~ ^[0-9]+$ ]]; then
            echo "${saved_port}"
            return
        fi
    fi

    local candidate
    for candidate in 3001 3002 3003 8080; do
        if ! is_port_listening "${candidate}"; then
            echo "${candidate}"
            return
        fi
    done

    echo "3004"
}

ollama_brew_available() {
    command -v brew >/dev/null 2>&1 && brew list --versions ollama >/dev/null 2>&1
}

ollama_brew_running() {
    command -v brew >/dev/null 2>&1 && brew services list | grep -q "^ollama[[:space:]]\+started"
}

preferred_ollama_runtime() {
    case "${OLLAMA_RUNTIME:-}" in
        brew|docker)
            echo "${OLLAMA_RUNTIME}"
            return
            ;;
    esac

    if docker_container_exists "${OLLAMA_DOCKER_CONTAINER}"; then
        echo "docker"
        return
    fi

    echo "brew"
}
