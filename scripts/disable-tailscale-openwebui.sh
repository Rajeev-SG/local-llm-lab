#!/bin/bash
set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale is not installed."
  exit 1
fi

tailscale serve --https=443 off >/dev/null

echo "Tailscale Serve disabled for Open WebUI."
