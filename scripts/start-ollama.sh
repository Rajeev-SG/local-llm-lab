#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

echo "Starting Ollama service..."
if curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo "Ollama is already running"
else
    RUNTIME="$(preferred_ollama_runtime)"
    if [[ "${RUNTIME}" == "docker" ]] && docker_container_exists "${OLLAMA_DOCKER_CONTAINER}"; then
        if ollama_brew_running; then
            echo "Stopping Homebrew Ollama service so Docker can bind port 11434..."
            brew services stop ollama 2>/dev/null || true
            sleep 2
        fi

        if docker_container_running "${OLLAMA_DOCKER_CONTAINER}"; then
            echo "Ollama Docker container is already running"
        else
            docker start "${OLLAMA_DOCKER_CONTAINER}" >/dev/null
            echo "Started Ollama Docker container ${OLLAMA_DOCKER_CONTAINER}"
        fi
    elif ollama_brew_available; then
        if docker_container_running "${OLLAMA_DOCKER_CONTAINER}"; then
            echo "Stopping Docker Ollama container to free port 11434 for the Homebrew runtime..."
            docker stop "${OLLAMA_DOCKER_CONTAINER}" >/dev/null
        fi

        if ollama_brew_running; then
            echo "Ollama Homebrew service is already running"
        else
            brew services start ollama
            sleep 2
        fi
    else
        echo "✗ Ollama is not installed as a Homebrew service and Docker container ${OLLAMA_DOCKER_CONTAINER} was not found"
        exit 1
    fi
fi

# Verify it's responding
for i in {1..10}; do
    if curl -fsS "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
        echo "✓ Ollama is running and responding on ${OLLAMA_HOST}"
        exit 0
    fi
    sleep 1
done

echo "✗ Ollama started but not responding. Check logs: brew services log ollama"
exit 1
