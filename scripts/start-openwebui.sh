#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

echo "Starting Open WebUI..."

if ! curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo "✗ Ollama is not reachable at ${OLLAMA_HOST}"
    echo "Start it with: ${LAB_ROOT}/scripts/start-ollama.sh"
    exit 1
fi

PORT="$(preferred_openwebui_port)"
URL="http://localhost:${PORT}"

if docker_container_exists "${OPENWEBUI_CONTAINER_NAME}"; then
    if docker_container_running "${OPENWEBUI_CONTAINER_NAME}"; then
        echo "✓ Open WebUI is already running"
    else
        docker start "${OPENWEBUI_CONTAINER_NAME}" >/dev/null
        echo "✓ Open WebUI started"
    fi
else
    echo "Creating Open WebUI container on ${URL}"
    docker run -d \
        --name "${OPENWEBUI_CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${PORT}:${OPENWEBUI_INTERNAL_PORT}" \
        -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
        -v "${OPENWEBUI_VOLUME_NAME}:/app/backend/data" \
        "${OPENWEBUI_IMAGE}" >/dev/null
    echo "✓ Open WebUI container created"
fi

save_openwebui_port "${PORT}"

# Wait for it to be ready
echo "Waiting for Open WebUI to be ready..."
for i in {1..30}; do
    if curl -fsS "${URL}" > /dev/null 2>&1; then
        echo "✓ Open WebUI is running at ${URL}"
        exit 0
    fi
    sleep 1
done

echo "✗ Open WebUI container started but not responding at ${URL}"
echo "Check logs with: docker logs ${OPENWEBUI_CONTAINER_NAME}"
exit 1
