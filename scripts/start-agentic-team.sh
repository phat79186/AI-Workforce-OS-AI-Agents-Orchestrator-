#!/bin/bash
# Start the Agentic Team system (UI + CLI available)
# Usage: ./scripts/start-agentic-team.sh [--port PORT] [--debug]
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

PORT="${1:-5002}"
if [ "$1" = "--debug" ] || [ "$2" = "--debug" ]; then
    export FLASK_DEBUG=true
fi
export AGENTIC_UI_BACKEND_PORT="$PORT"
export PORT="$PORT"

echo "Starting Agentic Team UI on port $PORT"
echo "  Health: http://localhost:$PORT/health"
echo "  API:    http://localhost:$PORT/api/team/config"
echo ""
python agentic_team/ui/app.py
