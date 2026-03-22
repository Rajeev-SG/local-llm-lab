#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

echo "Stopping Ollama service..."
if ollama_brew_running; then
    brew services stop ollama 2>/dev/null || true
    echo "✓ Stopped Homebrew Ollama service"
elif docker_container_running "${OLLAMA_DOCKER_CONTAINER}"; then
    docker stop "${OLLAMA_DOCKER_CONTAINER}" >/dev/null
    echo "✓ Stopped Docker container ${OLLAMA_DOCKER_CONTAINER}"
else
    brew services stop ollama 2>/dev/null || true
fi

# Verify it's stopped
sleep 1
if curl -fsS "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
    echo "⚠ Ollama still responding, killing any remaining processes..."
    pkill -f "ollama serve" 2>/dev/null || true
    sleep 1
fi

echo "✓ Ollama stopped"
