"""Shared MCP tools that span both systems."""

from __future__ import annotations

import json

from fastmcp import Context

from mcp_server.engines import _engines


def register(mcp):
    """Register shared tools."""

    @mcp.tool(annotations={"readOnlyHint": True})
    async def list_engines(ctx: Context) -> str:
        """List both engines and their current status."""
        engines = []

        orch = _engines.get("orchestrator")
        orch_err = _engines.get("orchestrator_error")
        if orch:
            engines.append(
                {
                    "name": "orchestrator",
                    "status": "healthy",
                    "agents": list(orch.adapters.keys()),
                    "workflows": orch.get_workflows(),
                }
            )
        else:
            engines.append({"name": "orchestrator", "status": "unavailable", "error": orch_err})

        at = _engines.get("agentic_team")
        at_err = _engines.get("agentic_team_error")
        if at:
            engines.append(
                {
                    "name": "agentic_team",
                    "status": "healthy",
                    "agents": at.get_available_agents(),
                    "team_valid": at.validate_team_bindings().get("valid"),
                }
            )
        else:
            engines.append({"name": "agentic_team", "status": "unavailable", "error": at_err})

        return json.dumps({"engines": engines}, indent=2)
