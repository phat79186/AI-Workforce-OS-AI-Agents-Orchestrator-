"""Tests for the MCP server and clients.

Uses FastMCP's in-memory Client for fast, subprocess-free testing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.adapters.base import AgentResponse

# We need to patch the engines before importing the server so the lifespan
# doesn't try to initialise real adapters (which call shutil.which).


def _mock_orchestrator():
    """Create a mock Orchestrator that behaves like the real one."""
    mock = MagicMock()
    mock.adapters = {"codex": MagicMock(), "gemini": MagicMock(), "claude": MagicMock()}
    mock.get_available_agents.return_value = ["codex", "gemini", "claude"]
    mock.get_workflows.return_value = ["default", "quick", "thorough"]
    mock.config = {
        "agents": {
            "codex": {"role": "implementation", "type": "cli"},
            "gemini": {"role": "review", "type": "cli"},
            "claude": {"role": "refinement", "type": "cli"},
        },
        "workflows": {
            "default": [
                {"agent": "codex", "task": "implement"},
                {"agent": "gemini", "task": "review"},
                {"agent": "claude", "task": "refine"},
            ],
            "quick": [{"agent": "codex", "task": "implement"}],
            "thorough": [
                {"agent": "codex", "task": "implement"},
                {"agent": "gemini", "task": "review"},
                {"agent": "claude", "task": "refine"},
            ],
        },
    }
    mock._extract_workflow_steps.side_effect = lambda wf: wf if isinstance(wf, list) else []
    mock.is_offline_mode = False
    mock.execute_task.return_value = {
        "success": True,
        "workflow": "default",
        "iterations": [
            {
                "steps": [
                    {"agent": "codex", "task": "implement", "success": True},
                    {"agent": "gemini", "task": "review", "success": True},
                    {"agent": "claude", "task": "refine", "success": True},
                ],
                "final_output": "Implemented and refined",
            }
        ],
        "final_output": "Implemented and refined",
    }
    return mock


def _mock_agentic_team():
    """Create a mock AgenticTeamEngine."""
    mock = MagicMock()
    mock.get_available_agents.return_value = ["claude", "codex", "gemini"]
    mock.get_team_config.return_value = {
        "lead_role": "project_manager",
        "max_turns": 12,
        "roles": {
            "project_manager": {
                "title": "Project Manager",
                "agent": "claude",
                "responsibilities": "Lead and finalise",
            },
            "software_developer": {
                "title": "Software Developer",
                "agent": "codex",
                "responsibilities": "Implement code",
            },
        },
    }
    mock.validate_team_bindings.return_value = {
        "valid": True,
        "available_agents": ["claude", "codex", "gemini"],
        "missing_roles": [],
        "reason": "",
    }
    mock.is_offline_mode = False
    mock.execute_task.return_value = {
        "success": True,
        "termination_reason": "lead_finalize",
        "stats": {"turns_executed": 3, "fallback_count": 0, "lead_escalation_count": 0},
        "duration_ms": 150,
        "final_output": "Team completed the task",
        "iterations": [{"steps": [], "final_output": "Team completed the task"}],
    }
    return mock


@pytest.fixture
def mcp_server():
    """Create the MCP server with mocked engines."""
    from mcp_server.engines import _engines
    from mcp_server.server import mcp

    _engines["orchestrator"] = _mock_orchestrator()
    _engines["orchestrator_error"] = None
    _engines["agentic_team"] = _mock_agentic_team()
    _engines["agentic_team_error"] = None
    return mcp


# Helper to run tool calls against the mock server
async def _call(server, tool_name, args=None):
    from fastmcp import Client

    async with Client(server) as c:
        result = await c.call_tool(tool_name, args or {})
        # Return parsed JSON from the text content
        text = result.content[0].text if result.content else "{}"
        return json.loads(text)


async def _list_tools(server):
    from fastmcp import Client

    async with Client(server) as c:
        return await c.list_tools()


async def _list_resources(server):
    from fastmcp import Client

    async with Client(server) as c:
        return await c.list_resources()


# ===================================================================
# Tool listing
# ===================================================================


class TestToolDiscovery:
    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_server):
        tools = await _list_tools(mcp_server)
        tool_names = {t.name for t in tools}
        expected = {
            "orchestrator_execute",
            "orchestrator_list_agents",
            "orchestrator_list_workflows",
            "orchestrator_health",
            "agentic_team_execute",
            "agentic_team_list_agents",
            "agentic_team_config",
            "agentic_team_validate",
            "agentic_team_health",
            "list_engines",
        }
        assert expected.issubset(tool_names), f"Missing: {expected - tool_names}"

    @pytest.mark.asyncio
    async def test_list_resources(self, mcp_server):
        resources = await _list_resources(mcp_server)
        uris = {str(r.uri) for r in resources}
        assert "config://orchestrator" in uris
        assert "config://agentic-team" in uris


# ===================================================================
# Orchestrator tools
# ===================================================================


class TestOrchestratorTools:
    @pytest.mark.asyncio
    async def test_execute_task(self, mcp_server):
        result = await _call(
            mcp_server,
            "orchestrator_execute",
            {"task": "Build a calculator", "workflow": "default", "max_iterations": 2},
        )
        data = result
        assert data["success"] is True
        assert data["workflow"] == "default"
        assert len(data["steps"]) == 3

    @pytest.mark.asyncio
    async def test_execute_empty_task_fails(self, mcp_server):
        with pytest.raises(Exception, match="empty"):
            await _call(mcp_server, "orchestrator_execute", {"task": ""})

    @pytest.mark.asyncio
    async def test_list_agents(self, mcp_server):
        result = await _call(mcp_server, "orchestrator_list_agents", {})
        data = result
        assert data["count"] == 3
        names = [a["name"] for a in data["agents"]]
        assert "codex" in names

    @pytest.mark.asyncio
    async def test_list_workflows(self, mcp_server):
        result = await _call(mcp_server, "orchestrator_list_workflows", {})
        data = result
        assert "default" in data["workflows"]

    @pytest.mark.asyncio
    async def test_health(self, mcp_server):
        result = await _call(mcp_server, "orchestrator_health", {})
        data = result
        assert data["status"] == "healthy"
        assert data["agents"] == 3


# ===================================================================
# Agentic Team tools
# ===================================================================


class TestAgenticTeamTools:
    @pytest.mark.asyncio
    async def test_execute_task(self, mcp_server):
        result = await _call(
            mcp_server,
            "agentic_team_execute",
            {"task": "Design a microservice", "max_turns": 5},
        )
        data = result
        assert data["success"] is True
        assert data["termination_reason"] == "lead_finalize"
        assert data["turns_executed"] == 3

    @pytest.mark.asyncio
    async def test_execute_empty_task_fails(self, mcp_server):
        with pytest.raises(Exception, match="empty"):
            await _call(mcp_server, "agentic_team_execute", {"task": "   "})

    @pytest.mark.asyncio
    async def test_list_agents(self, mcp_server):
        result = await _call(mcp_server, "agentic_team_list_agents", {})
        data = result
        assert data["count"] == 3

    @pytest.mark.asyncio
    async def test_team_config(self, mcp_server):
        result = await _call(mcp_server, "agentic_team_config", {})
        data = result
        assert data["lead_role"] == "project_manager"
        assert "project_manager" in data["roles"]

    @pytest.mark.asyncio
    async def test_validate(self, mcp_server):
        result = await _call(mcp_server, "agentic_team_validate", {})
        data = result
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_health(self, mcp_server):
        result = await _call(mcp_server, "agentic_team_health", {})
        data = result
        assert data["status"] == "healthy"


# ===================================================================
# Shared tools
# ===================================================================


class TestSharedTools:
    @pytest.mark.asyncio
    async def test_list_engines(self, mcp_server):
        result = await _call(mcp_server, "list_engines", {})
        data = result
        engines = {e["name"]: e for e in data["engines"]}
        assert "orchestrator" in engines
        assert "agentic_team" in engines
        assert engines["orchestrator"]["status"] == "healthy"
        assert engines["agentic_team"]["status"] == "healthy"


# ===================================================================
# MCP Client wrappers
# ===================================================================


class TestOrchestratorMCPClient:
    @pytest.mark.asyncio
    async def test_client_execute(self, mcp_server):
        from orchestrator.mcp_client import OrchestratorMCPClient

        client = OrchestratorMCPClient()
        result = await client.execute_task("Build a calculator")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_client_health(self, mcp_server):
        from orchestrator.mcp_client import OrchestratorMCPClient

        client = OrchestratorMCPClient()
        result = await client.health()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_client_list_agents(self, mcp_server):
        from orchestrator.mcp_client import OrchestratorMCPClient

        client = OrchestratorMCPClient()
        result = await client.list_agents()
        assert result["count"] == 3


class TestAgenticTeamMCPClient:
    @pytest.mark.asyncio
    async def test_client_execute(self, mcp_server):
        from agentic_team.mcp_client import AgenticTeamMCPClient

        client = AgenticTeamMCPClient()
        result = await client.execute_task("Design architecture")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_client_health(self, mcp_server):
        from agentic_team.mcp_client import AgenticTeamMCPClient

        client = AgenticTeamMCPClient()
        result = await client.health()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_client_validate(self, mcp_server):
        from agentic_team.mcp_client import AgenticTeamMCPClient

        client = AgenticTeamMCPClient()
        result = await client.validate()
        assert result["valid"] is True
