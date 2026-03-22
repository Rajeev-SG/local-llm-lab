#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

echo "Stopping Open WebUI..."

if docker_container_running "${OPENWEBUI_CONTAINER_NAME}"; then
    docker stop "${OPENWEBUI_CONTAINER_NAME}" >/dev/null
    echo "✓ Open WebUI stopped"
else
    echo "Open WebUI is not running"
fi
