#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="${ROOT_DIR}/broker/agent_offload.py"
TMP_DIR="${ROOT_DIR}/tmp/test-agent-offload"
mkdir -p "${TMP_DIR}"

run_case() {
  local name="$1"
  local goal="$2"
  local task_kind="$3"
  local role="$4"
  local input_file="$5"

  echo "== ${name} =="
  uv run --with fastmcp python "${BROKER}" estimate \
    --goal "${goal}" \
    --task-kind "${task_kind}" \
    --preferred-role "${role}" \
    --input-file "${input_file}"
  echo ""
  uv run --with fastmcp python "${BROKER}" run-task \
    --goal "${goal}" \
    --task-kind "${task_kind}" \
    --preferred-role "${role}" \
    --input-file "${input_file}"
  echo ""
}

cat > "${TMP_DIR}/small.txt" <<'EOF'
Command output:
- Found 9 files touching OpenRouter wrappers
- The largest risk is duplicated model routing across env.sh, settings.json, and harness-specific configs
- The likely goal is to centralize routing and add one shared broker
EOF

python3 - <<'PY' > "${TMP_DIR}/large.txt"
text = "This is a long multi-document context block for escalation testing. " * 1200
print(text)
PY

cat > "${TMP_DIR}/code.txt" <<'EOF'
diff --git a/broker.py b/broker.py
+ Added role routing based on task kind
+ Added OpenRouter provider max_price guardrails
+ Added cache writes keyed by model and prompt
+ Added codex transcript audit helper
EOF

run_case "Default worker" "Compress shell findings for a stronger agent" "summarize_tool_output" "auto" "${TMP_DIR}/small.txt"
run_case "Long context escalator" "Distill a large context pack into a short briefing" "cross_doc_synthesis" "auto" "${TMP_DIR}/large.txt"
run_case "Harder mid-cost worker" "Prepare a harder synthesis memo with tradeoffs" "hard_synthesis" "auto" "${TMP_DIR}/small.txt"
run_case "Coding specialist" "Extract the important diff behavior for code review" "diff_summary" "auto" "${TMP_DIR}/code.txt"

echo "== Codex efficiency audit =="
uv run --with fastmcp python "${BROKER}" audit-codex
echo ""
echo "== Scenario comparison =="
uv run --with fastmcp python "${BROKER}" compare-scenario --raw-chars 388722 --compressed-chars 30000 --main-model-prompt-per-million 1.25

