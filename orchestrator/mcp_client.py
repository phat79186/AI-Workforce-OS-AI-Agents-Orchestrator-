"""MCP Client for the Orchestrator.

Connects to the AI Coding Tools MCP server and provides a clean Python API
for invoking tools. Can connect in-memory (same process) or over HTTP.

Usage:
    # In-memory (for testing or embedded use)
    from orchestrator.mcp_client import OrchestratorMCPClient
    client = OrchestratorMCPClient()
    result = await client.execute_task("Build a REST API")

    # Remote HTTP server
    client = OrchestratorMCPClient(server_url="http://localhost:8000/mcp")
    result = await client.execute_task("Build a REST API")
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class OrchestratorMCPClient:
    """High-level client for orchestrator MCP tools.

    Connects to the MCP server for orchestrator operations.
    """

    def __init__(self, server_url: str | None = None):
        """Initialize the orchestrator MCP client.

        Args:
            server_url: HTTP URL of the MCP server (e.g. http://localhost:8000/mcp).
                        If None, connects in-memory to the local server instance.
        """
        self._server_url = server_url
        self._client = None

    async def _get_client(self):
        """Lazily create the FastMCP client."""
        if self._client is None:
            from fastmcp import Client

            if self._server_url:
                self._client = Client(self._server_url)
            else:
                # In-memory — import and connect to the local server directly
                from mcp_server.server import mcp as server_instance

                self._client = Client(server_instance)
        return self._client

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool and return parsed JSON result."""
        client = await self._get_client()
        async with client:
            result = await client.call_tool(name, arguments)
            text = result.content[0].text if result.content else "{}"
            return json.loads(text)

    # --- Orchestrator-specific methods ---

    async def execute_task(
        self,
        task: str,
        workflow: str = "default",
        max_iterations: int = 3,
    ) -> dict[str, Any]:
        """Execute a task through an orchestrator workflow.

        Args:
            task: The software engineering task description.
            workflow: Workflow name (default, quick, thorough, etc.).
            max_iterations: Maximum refinement iterations.

        Returns:
            Result dict with success, final_output, steps, etc.
        """
        return await self._call_tool(
            "orchestrator_execute",
            {
                "task": task,
                "workflow": workflow,
                "max_iterations": max_iterations,
            },
        )

    async def list_agents(self) -> dict[str, Any]:
        """List available orchestrator agents."""
        return await self._call_tool("orchestrator_list_agents", {})

    async def list_workflows(self) -> dict[str, Any]:
        """List available workflows."""
        return await self._call_tool("orchestrator_list_workflows", {})

    async def health(self) -> dict[str, Any]:
        """Check orchestrator health."""
        return await self._call_tool("orchestrator_health", {})

    async def list_engines(self) -> dict[str, Any]:
        """List all engines (orchestrator + agentic team)."""
        return await self._call_tool("list_engines", {})
