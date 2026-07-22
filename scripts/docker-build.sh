#!/bin/bash
# Build Docker image for both services
set -e
cd "$(dirname "$0")/.."

TAG="${1:-ai-coding-tools:latest}"
echo "Building Docker image: $TAG"
docker build -t "$TAG" .
echo ""
echo "Built: $TAG"
echo "  Run orchestrator:  docker run -p 5001:5001 $TAG"
echo "  Run agentic team:  docker run -p 5002:5002 -e PORT=5002 $TAG agentic_team/ui/app.py"
