#!/bin/bash
# Check health of both services
set -e
cd "$(dirname "$0")/.."

echo "=== Health Check ==="
echo ""

for svc in "Orchestrator:5001" "Agentic Team:5002"; do
    name="${svc%%:*}"
    port="${svc##*:}"
    status=$(curl -sf "http://localhost:$port/health" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unreachable")
    if [ "$status" = "healthy" ]; then
        echo "  [OK] $name (port $port): $status"
    else
        echo "  [!!] $name (port $port): $status"
    fi
done
