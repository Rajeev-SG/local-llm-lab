#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Local LLM Lab - Status Dashboard                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Ollama Status
echo "━━━ Ollama ━━━"
if curl -fsS "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
    echo "Status: ✓ Running"
    echo "Endpoint: ${OLLAMA_HOST}"
    if ollama_brew_running; then
        echo "Runtime: Homebrew service"
    elif docker_container_running "${OLLAMA_DOCKER_CONTAINER}"; then
        echo "Runtime: Docker container (${OLLAMA_DOCKER_CONTAINER})"
    fi
    echo ""
    echo "Models:"
    ollama list | tail -n +1 | while read -r line; do
        echo "  • ${line}"
    done
else
    echo "Status: ✗ Not running"
    echo "Start with: ${LAB_ROOT}/scripts/start-ollama.sh"
fi

echo ""

# Open WebUI Status
echo "━━━ Open WebUI ━━━"
PORT="$(preferred_openwebui_port)"
URL="http://localhost:${PORT}"

if docker_container_running "${OPENWEBUI_CONTAINER_NAME}"; then
    echo "Status: ✓ Running"
    echo "Runtime: Docker container (${OPENWEBUI_CONTAINER_NAME})"
    echo "URL: ${URL}"
elif docker_container_exists "${OPENWEBUI_CONTAINER_NAME}"; then
    echo "Status: ⏸ Stopped"
    echo "Runtime: Docker container (${OPENWEBUI_CONTAINER_NAME})"
    echo "Start with: ${LAB_ROOT}/scripts/start-openwebui.sh"
elif curl -fsS "${URL}" > /dev/null 2>&1; then
    echo "Status: ⚠ Something else is responding"
    echo "URL: ${URL}"
    echo "Note: Port ${PORT} is in use by a non-Open WebUI process"
else
    echo "Status: ✗ Not running"
    echo "Start with: ${LAB_ROOT}/scripts/start-openwebui.sh"
fi

echo ""

# Tailscale remote access
echo "━━━ Tailscale Remote Access ━━━"
if command -v tailscale >/dev/null 2>&1; then
    TS_STATE="$(tailscale status --json 2>/dev/null | jq -r '.BackendState // empty')"
    if [[ "${TS_STATE}" == "Running" ]]; then
        TS_URL="$(
            tailscale serve status --json 2>/dev/null \
                | jq -r '.Web | keys[0] // empty | sub(":443$"; "") | "https://" + . + "/"'
        )"
        if [[ -n "${TS_URL}" ]]; then
            echo "Status: ✓ Private remote access enabled"
            echo "URL: ${TS_URL}"
            echo "Scope: Only devices signed into the same Tailscale tailnet"
        else
            echo "Status: ⏸ Tailscale connected, no Open WebUI serve rule"
            echo "Enable with: ${LAB_ROOT}/scripts/enable-tailscale-openwebui.sh"
        fi
    else
        echo "Status: ✗ Tailscale not connected"
        echo "Enable with: tailscale up"
    fi
else
    echo "Status: ✗ Tailscale CLI not installed"
fi

echo ""

# Memory usage
echo "━━━ System Memory ━━━"
if command -v sysctl &> /dev/null; then
    MEM_TOTAL=$(sysctl -n hw.memsize | awk '{print int($1/1073741824) " GB"}')
    echo "Total: ${MEM_TOTAL}"
fi

if command -v memory_pressure &> /dev/null; then
    memory_pressure 2>/dev/null || echo "Pressure: N/A"
fi

echo ""

# Quick tips
echo "━━━ Quick Commands ━━━"
echo "Chat with model:    ollama run mistral-small:22b"
echo "Open WebUI:         open ${URL}"
echo "Private anywhere:   ${LAB_ROOT}/scripts/enable-tailscale-openwebui.sh"
echo "Test all models:    ${LAB_ROOT}/scripts/test-models.sh"
echo "Benchmark:          ${LAB_ROOT}/scripts/benchmark-model.sh mistral-small:22b"
echo "Broker test sweep:  ${LAB_ROOT}/scripts/test-agent-offload.sh"
