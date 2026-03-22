#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale is not installed."
  exit 1
fi

if ! tailscale status --json >/dev/null 2>&1; then
  echo "tailscale is not running."
  exit 1
fi

PORT="$(preferred_openwebui_port)"
URL="http://127.0.0.1:${PORT}"

if ! curl -fsS "${URL}" >/dev/null 2>&1; then
  echo "Open WebUI is not responding on ${URL}"
  echo "Start it with: ${LAB_ROOT}/scripts/start-openwebui.sh"
  exit 1
fi

tailscale serve --bg "${PORT}" >/dev/null

TAILSCALE_URL="$(
  tailscale serve status --json \
    | jq -r '.Web | keys[0] // empty | sub(":443$"; "") | "https://" + . + "/"'
)"

echo "Tailscale Serve enabled for Open WebUI."
echo "Private URL: ${TAILSCALE_URL}"
echo "Only devices signed into the same tailnet can reach this URL."
