#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${PLAYWRIGHT_SESSION:-openwebui-proof}"
URL="${OPENWEBUI_URL:-http://localhost:$(cat "${ROOT_DIR}/.openwebui-port" 2>/dev/null || printf '3001')}"
ARTIFACT_DIR="${ROOT_DIR}/output/acceptance/openwebui-proof/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "${ARTIFACT_DIR}"

command -v playwright-cli >/dev/null || { echo "playwright-cli is required" >&2; exit 1; }
playwright-cli -s="${SESSION}" open "${URL}"
playwright-cli -s="${SESSION}" snapshot > "${ARTIFACT_DIR}/before.md"
playwright-cli -s="${SESSION}" screenshot --filename "${ARTIFACT_DIR}/before.png"
printf 'Opened isolated Open WebUI proof session %s at %s\n' "${SESSION}" "${URL}"
printf 'Complete one chat manually in this session, then run:\n'
printf '  playwright-cli -s=%s snapshot > %s/after.md\n' "${SESSION}" "${ARTIFACT_DIR}"
printf '  playwright-cli -s=%s screenshot --filename %s/after.png\n' "${SESSION}" "${ARTIFACT_DIR}"
printf 'No live browser profile, cookies, or token cache is used.\n'
