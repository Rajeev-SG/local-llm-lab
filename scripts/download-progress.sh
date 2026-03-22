#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

# Visual progress tracker for Ollama model downloads

MODELS=("qwen3:30b" "deepseek-r1:32b" "qwen2.5:72b" "qwen3-coder:30b")
MODEL_DIR="$HOME/.ollama/models"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Expected sizes in GB (approximate) - using simple function instead of associative array
get_expected_size() {
    local model="$1"
    case "$model" in
        "qwen3:30b")        echo "18" ;;
        "qwen3-coder:30b")  echo "18" ;;
        "deepseek-r1:32b")  echo "19" ;;
        "qwen2.5:72b")      echo "47" ;;
        *)                  echo "20" ;;
    esac
}

# Get current download progress from Ollama
get_download_progress() {
    local model="$1"
    local model_name="${model%%:*}"

    # Check if model exists in ollama list (fully downloaded)
    if ollama list 2>/dev/null | grep -q "^${model_name}"; then
        echo "100"
        return
    fi

    # Check blob directory for partial downloads
    local blobs_dir="$MODEL_DIR/blobs"
    if [[ -d "$blobs_dir" ]]; then
        # Calculate total size of blobs
        local total_size=$(du -sm "$blobs_dir" 2>/dev/null | cut -f1)
        local expected_size=$(get_expected_size "$model")
        local expected_mb=$((expected_size * 1024))
        if [[ -n "${total_size:-0}" && "${total_size:-0}" -gt 0 ]]; then
            local pct=$((total_size * 100 / expected_mb))
            if [[ $pct -gt 100 ]]; then
                pct=99
            fi
            echo "$pct"
            return
        fi
    fi

    echo "0"
}

# Draw progress bar
draw_bar() {
    local percent=$1
    local width=30
    local filled=$((percent * width / 100))
    local empty=$((width - filled))

    local bar=""
    local i
    for ((i=0; i<filled; i++)); do
        bar+="█"
    done
    for ((i=0; i<empty; i++)); do
        bar+="░"
    done

    echo "$bar"
}

# Main display
clear
echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║           🤖 Ollama Model Download Progress Tracker            ║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Ollama status
if ! curl -fsS "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
    echo -e "${RED}✗ Ollama is not running${NC}"
    echo "  Start with: ${LAB_ROOT}/scripts/start-ollama.sh"
    exit 1
fi

echo -e "${BOLD}Model Downloads${NC}"
echo -e "${BOLD}───────────────${NC}"
echo ""

total_progress=0
completed=0

for model in "${MODELS[@]}"; do
    progress=$(get_download_progress "$model")
    expected_size=$(get_expected_size "$model")
    bar=$(draw_bar "$progress")

    if [[ "$progress" -eq 100 ]]; then
        echo -e "  ${GREEN}✓${NC} ${model}"
        echo -e "    ${GREEN}${bar}${NC} ${progress}%"
        echo -e "    ${GREEN}Complete (~${expected_size}GB)${NC}"
        ((completed++))
    elif [[ "$progress" -gt 0 ]]; then
        echo -e "  ${YELLOW}⏳${NC} ${model}"
        echo -e "    ${YELLOW}${bar}${NC} ${progress}%"
        echo -e "    ${CYAN}Downloading (~${expected_size}GB expected)${NC}"
    else
        echo -e "  ${BLUE}○${NC} ${model}"
        echo -e "    ${BLUE}${bar}${NC} ${progress}%"
        echo -e "    ${BLUE}Pending (~${expected_size}GB expected)${NC}"
    fi
    echo ""

    total_progress=$((total_progress + progress))
done

# Overall progress
avg_progress=$((total_progress / ${#MODELS[@]}))
overall_bar=$(draw_bar "$avg_progress")

echo -e "${BOLD}───────────────${NC}"
echo -e "${BOLD}Overall Progress${NC}"
echo -e "  ${overall_bar} ${avg_progress}%"
echo -e "  ${completed}/${#MODELS[@]} models complete"
echo ""

# Disk usage
echo -e "${BOLD}Disk Usage${NC}"
echo -e "${BOLD}──────────${NC}"
if [[ -d "$MODEL_DIR" ]]; then
    used=$(du -sh "$MODEL_DIR" 2>/dev/null | cut -f1)
    echo -e "  Models directory: ${used}"
fi
echo ""

# Open WebUI status
echo -e "${BOLD}Open WebUI${NC}"
echo -e "${BOLD}──────────${NC}"
OPENWEBUI_PORT="$(preferred_openwebui_port)"
OPENWEBUI_URL="http://localhost:${OPENWEBUI_PORT}"
if docker_container_running "${OPENWEBUI_CONTAINER_NAME}"; then
    echo -e "  ${GREEN}✓ Running at ${OPENWEBUI_URL}${NC}"
elif docker_container_exists "${OPENWEBUI_CONTAINER_NAME}"; then
    echo -e "  ${YELLOW}⏸ Stopped${NC}"
else
    echo -e "  ${BLUE}○ Not running${NC}"
fi
echo ""

# Tips
echo -e "${BOLD}────────────────────────────────────────────────────────────────${NC}"
if [[ $completed -lt ${#MODELS[@]} ]]; then
    echo -e "${CYAN}💡 Models download in parallel. Total ~100GB for all 4 models.${NC}"
    echo -e "${CYAN}   Run this script anytime to check progress:${NC}"
    echo -e "   ${BOLD}~/local-llm-lab/scripts/download-progress.sh${NC}"
    echo ""
    echo -e "${CYAN}   Or watch continuously:${NC}"
    echo -e "   ${BOLD}~/local-llm-lab/scripts/watch-downloads.sh${NC}"
else
    echo -e "${GREEN}✓ All models downloaded! Ready to use.${NC}"
    echo -e "   Chat: ${BOLD}ollama run qwen3:30b${NC}"
    echo -e "   Status: ${BOLD}~/local-llm-lab/scripts/status.sh${NC}"
fi
