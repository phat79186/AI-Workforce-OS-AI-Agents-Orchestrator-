#!/bin/bash
# Start MCP Server — exposes both engines to MCP clients
# Usage:
#   ./scripts/start-mcp-server.sh              # stdio (Claude Desktop)
#   ./scripts/start-mcp-server.sh --http       # HTTP on port 8000
#   ./scripts/start-mcp-server.sh --http 9000  # HTTP on custom port
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

if [ "$1" = "--http" ]; then
    PORT="${2:-8000}"
    echo "Starting MCP Server (HTTP) on port $PORT"
    echo "  Endpoint: http://localhost:$PORT/mcp"
    python -m mcp_server.server --transport http --port "$PORT"
else
    echo "Starting MCP Server (stdio)"
    echo "  Connect via Claude Desktop or fastmcp client"
    python -m mcp_server.server
fi
