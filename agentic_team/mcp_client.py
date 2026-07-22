"""MCP Client for the Agentic Team.

Connects to the AI Coding Tools MCP server and provides a clean Python API
for invoking agentic team tools. Can connect in-memory or over HTTP.

Usage:
    from agentic_team.mcp_client import AgenticTeamMCPClient
    client = AgenticTeamMCPClient()
    result = await client.execute_task("Design a microservice architecture")
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AgenticTeamMCPClient:
    """High-level client for agentic team MCP tools.

    Connects to the AI Coding Tools MCP server and provides a clean Python API
    for invoking agentic team tools.
    """

    def __init__(self, server_url: str | None = None):
        """Initialize the agentic team MCP client.

        Args:
            server_url: HTTP URL of the MCP server (e.g. http://localhost:8000/mcp).
                        If None, connects in-memory to the local server instance.
        """
        self._server_url = server_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from fastmcp import Client

            if self._server_url:
                self._client = Client(self._server_url)
            else:
                from mcp_server.server import mcp as server_instance

                self._client = Client(server_instance)
        return self._client

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        async with client:
            result = await client.call_tool(name, arguments)
            text = result.content[0].text if result.content else "{}"
            return json.loads(text)

    # --- Agentic Team methods ---

    async def execute_task(
        self,
        task: str,
        max_turns: int = 12,
    ) -> dict[str, Any]:
        """Execute a task with the role-based agentic team.

        Args:
            task: The task for the team to collaborate on.
            max_turns: Maximum team communication turns.

        Returns:
            Result dict with success, final_output, turn_log, etc.
        """
        return await self._call_tool(
            "agentic_team_execute",
            {
                "task": task,
                "max_turns": max_turns,
            },
        )

    async def list_agents(self) -> dict[str, Any]:
        """List available agentic team agents."""
        return await self._call_tool("agentic_team_list_agents", {})

    async def team_config(self) -> dict[str, Any]:
        """Get team role configuration."""
        return await self._call_tool("agentic_team_config", {})

    async def validate(self) -> dict[str, Any]:
        """Validate team bindings."""
        return await self._call_tool("agentic_team_validate", {})

    async def health(self) -> dict[str, Any]:
        """Check agentic team health."""
        return await self._call_tool("agentic_team_health", {})

    async def list_engines(self) -> dict[str, Any]:
        """List all engines (orchestrator + agentic team)."""
        return await self._call_tool("list_engines", {})
