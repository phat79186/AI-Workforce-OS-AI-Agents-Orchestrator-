#!/bin/bash
# Auto-format all Python code
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

echo "Formatting with Black..."
black orchestrator/ agentic_team/ tests/

echo "Sorting imports with isort..."
isort orchestrator/ agentic_team/ tests/

echo "Done."
