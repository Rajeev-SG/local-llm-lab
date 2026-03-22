#!/usr/bin/env bash
# Continuous download progress watcher
# Updates every 5 seconds until all downloads complete

MODELS=("qwen3:30b" "deepseek-r1:32b" "qwen2.5:72b" "qwen3-coder:30b")
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

check_complete() {
    local complete=0
    local model_name
    for model in "${MODELS[@]}"; do
        model_name="${model%%:*}"
        if ollama list 2>/dev/null | grep -q "^${model_name}"; then
            ((complete++)) || true
        fi
    done
    echo $complete
}

# Watch loop
while true; do
    clear
    "$SCRIPT_DIR/download-progress.sh"

    completed=$(check_complete)
    if [[ $completed -eq ${#MODELS[@]} ]]; then
        echo ""
        echo -e "\033[0;32m✓ All downloads complete!\033[0m"
        break
    fi

    echo ""
    echo -e "\033[0;90mRefreshing in 5 seconds... (Ctrl+C to exit)\033[0m"
    sleep 5
done
