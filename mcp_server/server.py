"""
MCP Server for AI Coding Tools — assembly module.

Creates the FastMCP instance and registers tools/resources from submodules.
Engine lifecycle is managed by ``engines.py``.

Usage:
    python -m mcp_server.server                              # stdio
    python -m mcp_server.server --transport http --port 8000  # HTTP
    fastmcp dev mcp_server/server.py:mcp                     # Inspector
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server.engines import _engines, init_engines  # noqa: E402

logger = logging.getLogger("mcp_server")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialise engines at startup (skips if already set by tests)."""
    logger.info("MCP server starting")
    if _engines.get("orchestrator") is None and _engines.get("orchestrator_error") is None:
        init_engines()
    yield
    logger.info("MCP server shutting down")


# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="AI Coding Tools",
    instructions=(
        "Provides tools to execute software engineering tasks using two independent "
        "AI multi-agent systems: the Orchestrator (workflow-based) and the Agentic "
        "Team (role-based). Use orchestrator_execute for predefined workflows and "
        "agentic_team_execute for free-form team collaboration."
    ),
    version="2.0.0",
    lifespan=lifespan,
    on_duplicate="error",
)


# ---------------------------------------------------------------------------
# Register tools and resources from submodules
# ---------------------------------------------------------------------------

from mcp_server.resources import config_resources  # noqa: E402
from mcp_server.tools import (  # noqa: E402
    agentic_team_tools,
    code_analysis,
    context_tools,
    devops_tools,
    orchestrator_tools,
    security_tools,
    shared_tools,
    testing_tools,
)

orchestrator_tools.register(mcp)
agentic_team_tools.register(mcp)
shared_tools.register(mcp)
config_resources.register(mcp)

# Register new specialized tools
code_analysis.register_code_analysis_tools(mcp)
security_tools.register_security_tools(mcp)
testing_tools.register_testing_tools(mcp)
devops_tools.register_devops_tools(mcp)
context_tools.register_context_tools(mcp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Coding Tools MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()
