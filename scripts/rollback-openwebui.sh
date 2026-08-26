#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib.sh"
if [[ $# -ne 1 || "$1" =~ :main$|:latest$ || ! "$1" =~ ^ghcr\.io/open-webui/open-webui(:v[0-9][^[:space:]]*|@sha256:[a-f0-9]+)$ ]]; then
  echo "Usage: $0 ghcr.io/open-webui/open-webui:vX.Y.Z-or-digest" >&2
  exit 2
fi
export OPENWEBUI_IMAGE="$1"
"${ROOT_DIR}/scripts/setup-openwebui.sh"
echo "Rollback/recreate complete; volume ${OPENWEBUI_VOLUME_NAME:-open-webui-data} was not removed."
