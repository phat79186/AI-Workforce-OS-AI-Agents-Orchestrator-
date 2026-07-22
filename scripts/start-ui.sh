#!/bin/bash
# Start Orchestrator Web UI — run from project root
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate
echo "Starting Orchestrator UI on port ${PORT:-5001}"
python orchestrator/ui/app.py
