#!/usr/bin/env bash
# Launch the PrismML llama.cpp build serving Ternary Bonsai 2 27B (PQ2_0).
#
# Exact runtime + model pinned in config/bonsai2-27b.json. This script reads that
# file so the launch is reproducible.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$ROOT/config/bonsai2-27b.json"
BIN_DIR="$(python3 -c "import json,sys;print(json.load(open('$CFG'))['binary_dir'])")"
MODEL="$(python3 -c "import json,sys;print(json.load(open('$CFG'))['model_path'])")"
MMPROJ="$(python3 -c "import json,sys;print(json.load(open('$CFG'))['mmproj_path'])")"
PORT="${BONSAI_PORT:-8091}"
CTX="${BONSAI_CTX:-32768}"

exec "$BIN_DIR/llama-server" \
  -m "$MODEL" \
  --mmproj "$MMPROJ" \
  -ngl 99 -fa on -c "$CTX" \
  --host 127.0.0.1 --port "$PORT" \
  --jinja \
  --temp 1.0 --top-p 0.95 --top-k 20
