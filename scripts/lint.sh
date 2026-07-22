#!/bin/bash
# Run all linters
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

echo "=== Black ==="
black --check orchestrator/ agentic_team/ tests/ || true

echo ""
echo "=== isort ==="
isort --check-only orchestrator/ agentic_team/ tests/ || true

echo ""
echo "=== Flake8 ==="
flake8 orchestrator/ agentic_team/ tests/ || true

echo ""
echo "=== mypy ==="
mypy orchestrator/ agentic_team/ --ignore-missing-imports || true
