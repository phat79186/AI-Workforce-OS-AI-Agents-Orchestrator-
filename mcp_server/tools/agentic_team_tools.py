"""MCP tools for the Agentic Team system."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_server.engines import get_engine


def register(mcp):
    """Register all agentic team tools on the given FastMCP instance."""

    @mcp.tool(annotations={"readOnlyHint": False})
    async def agentic_team_execute(
        ctx: Context,
        task: Annotated[str, Field(description="The task for the team to collaborate on")],
        max_turns: Annotated[int, Field(ge=1, le=50, description="Max team turns")] = 12,
    ) -> str:
        """Execute a task with the agentic team using role-based collaboration.

        A team of 5 roles (Project Manager, Architect, Developer, QA, DevOps)
        communicates freely. The Project Manager gates final delivery.
        """
        engine = get_engine("agentic_team")

        if not task or not task.strip():
            raise ToolError("Task cannot be empty")
        if len(task) > 50000:
            raise ToolError("Task exceeds 50000 character limit")

        await ctx.info(f"Starting agentic team execution (max {max_turns} turns)")

        turn_log: list[str] = []

        def on_turn(step: dict[str, Any]):
            icon = ">>>" if step.get("action") == "finalize" else "-->"
            turn_log.append(
                f"  Turn {step.get('turn')}: {step.get('from_role')} {icon} "
                f"{step.get('to_role')} [{step.get('action')}]"
            )

        try:
            result = engine.execute_task(
                task=task.strip(),
                max_turns=max_turns,
                turn_callback=on_turn,
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"Execution failed: {exc}") from exc

        return json.dumps(
            {
                "success": result.get("success"),
                "termination_reason": result.get("termination_reason"),
                "turns_executed": result.get("stats", {}).get("turns_executed"),
                "duration_ms": result.get("duration_ms"),
                "turn_log": turn_log,
                "final_output": result.get("final_output", ""),
            },
            indent=2,
            default=str,
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def agentic_team_list_agents(ctx: Context) -> str:
        """List available agents in the agentic team."""
        engine = get_engine("agentic_team")
        return json.dumps(
            {
                "agents": engine.get_available_agents(),
                "count": len(engine.get_available_agents()),
            },
            indent=2,
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def agentic_team_config(ctx: Context) -> str:
        """Get team role configuration: roles, agents, and responsibilities."""
        engine = get_engine("agentic_team")
        tc = engine.get_team_config()
        roles = {}
        for name, spec in tc.get("roles", {}).items():
            roles[name] = {
                "title": spec.get("title", ""),
                "agent": spec.get("agent", ""),
                "responsibilities": spec.get("responsibilities", ""),
            }
        return json.dumps(
            {
                "lead_role": tc.get("lead_role"),
                "max_turns": tc.get("max_turns"),
                "roles": roles,
            },
            indent=2,
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def agentic_team_validate(ctx: Context) -> str:
        """Validate team configuration: check all roles map to available agents."""
        engine = get_engine("agentic_team")
        return json.dumps(engine.validate_team_bindings(), indent=2)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def agentic_team_health(ctx: Context) -> str:
        """Check agentic team health: status, team validity, agents."""
        engine = get_engine("agentic_team")
        validation = engine.validate_team_bindings()
        return json.dumps(
            {
                "status": "healthy" if validation.get("valid") else "degraded",
                "valid": validation.get("valid"),
                "agents": engine.get_available_agents(),
                "missing_roles": validation.get("missing_roles", []),
                "offline_mode": engine.is_offline_mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
