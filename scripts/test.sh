#!/bin/bash
# Run full test suite — run from project root
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

echo "Running tests..."
python -m pytest tests/ --override-ini="addopts=" -q --timeout=30

echo ""
echo "Running linters..."
black --check orchestrator/ agentic_team/ tests/ || true
isort --check-only orchestrator/ agentic_team/ tests/ || true
flake8 orchestrator/ agentic_team/ tests/ || true

echo ""
echo "Running type checks..."
mypy orchestrator/ agentic_team/ --ignore-missing-imports || true

echo ""
echo "Running security scan..."
bandit -r orchestrator/ agentic_team/ -c pyproject.toml || true

echo ""
echo "All checks complete."
