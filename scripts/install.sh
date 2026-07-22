#!/bin/bash
# Install AI Coding Tools — run from project root
set -e
cd "$(dirname "$0")/.."

echo "AI Coding Tools Installation"
echo ""

# Check Python
python3 --version || { echo "Python 3.8+ required"; exit 1; }

# Virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install deps
echo "Installing dependencies..."
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install -e .

# Pre-commit
if command -v pre-commit &>/dev/null; then
    pre-commit install
fi

# Directories
mkdir -p output workspace reports sessions logs

echo ""
echo "Installation complete."
echo "  Orchestrator UI:   python orchestrator/ui/app.py"
echo "  Agentic Team UI:   python agentic_team/ui/app.py"
echo "  CLI shell:         ./ai-orchestrator shell"
echo "  Run tests:         make test"
