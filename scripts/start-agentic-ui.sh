#!/bin/bash
# Start Agentic Team Web UI — run from project root
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate
echo "Starting Agentic Team UI on port ${AGENTIC_UI_BACKEND_PORT:-5002}"
python agentic_team/ui/app.py
