#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# YouTube Sales Transcript Analyzer — quick launcher
#
#  Usage:
#    ./run.sh "https://www.youtube.com/watch?v=VIDEO_ID"          # analyze
#    ./run.sh "https://www.youtube.com/watch?v=VIDEO_ID" --agent  # analyze + live agent
#    ./run.sh --interactive ./sales_outputs/sales_VIDEO_ID/sales_agent_prompt.txt
#
# The script looks for your API key in:
#   1. ANTHROPIC_API_KEY environment variable
#   2. sales_analyzer/.env  (ANTHROPIC_API_KEY=sk-ant-...)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER_DIR="$SCRIPT_DIR/sales_analyzer"

# ── Dependency check ─────────────────────────────────────────────────────────
if ! python3 -c "import youtube_transcript_api, anthropic" &>/dev/null; then
  echo "Installing dependencies..."
  pip3 install -q -r "$ANALYZER_DIR/requirements.txt"
fi

# ── API key check ─────────────────────────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  ENV_FILE="$ANALYZER_DIR/.env"
  if [[ -f "$ENV_FILE" ]]; then
    export ANTHROPIC_API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'")
  fi
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo ""
  echo "  ┌─────────────────────────────────────────────────────────┐"
  echo "  │  ANTHROPIC_API_KEY not set.                             │"
  echo "  │                                                         │"
  echo "  │  Option 1: export ANTHROPIC_API_KEY=sk-ant-...         │"
  echo "  │  Option 2: echo 'ANTHROPIC_API_KEY=sk-ant-...' >       │"
  echo "  │            sales_analyzer/.env                          │"
  echo "  └─────────────────────────────────────────────────────────┘"
  echo ""
  # Let main.py prompt for it interactively
fi

# ── Run ───────────────────────────────────────────────────────────────────────
exec python3 "$ANALYZER_DIR/main.py" "$@"
