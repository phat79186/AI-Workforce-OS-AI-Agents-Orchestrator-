#!/bin/bash
# Start both services with Docker Compose
set -e
cd "$(dirname "$0")/.."

echo "Starting services with Docker Compose..."
docker compose up --build -d

echo ""
echo "Services:"
echo "  Orchestrator:  http://localhost:5001"
echo "  Agentic Team:  http://localhost:5002"
echo ""
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
