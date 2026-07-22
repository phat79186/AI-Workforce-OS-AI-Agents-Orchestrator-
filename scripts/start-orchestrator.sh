#!/bin/bash
# Start the Orchestrator system (UI + CLI available)
# Usage: ./scripts/start-orchestrator.sh [--port PORT] [--debug]
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

PORT="${1:-5001}"
if [ "$1" = "--debug" ] || [ "$2" = "--debug" ]; then
    export FLASK_DEBUG=true
fi
export UI_BACKEND_PORT="$PORT"

echo "Starting Orchestrator UI on port $PORT"
echo "  Health: http://localhost:$PORT/health"
echo "  API:    http://localhost:$PORT/api/agents"
echo ""
python orchestrator/ui/app.py
