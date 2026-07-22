#!/bin/bash
# Start both Orchestrator (5001) and Agentic Team (5002) services
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $PID1 $PID2 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting both services..."
echo ""

UI_BACKEND_PORT=5001 python orchestrator/ui/app.py &
PID1=$!
echo "  Orchestrator UI:   http://localhost:5001 (PID $PID1)"

AGENTIC_UI_BACKEND_PORT=5002 PORT=5002 python agentic_team/ui/app.py &
PID2=$!
echo "  Agentic Team UI:   http://localhost:5002 (PID $PID2)"

echo ""
echo "Press Ctrl+C to stop both services"
wait
