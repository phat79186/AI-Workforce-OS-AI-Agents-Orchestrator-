"""MCP tools for the Orchestrator system."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_server.engines import get_engine


def register(mcp):
    """Register all orchestrator tools on the given FastMCP instance."""

    @mcp.tool(annotations={"readOnlyHint": False})
    async def orchestrator_execute(
        ctx: Context,
        task: Annotated[str, Field(description="The software engineering task to execute")],
        workflow: Annotated[str, Field(description="Workflow name")] = "default",
        max_iterations: Annotated[
            int, Field(ge=1, le=10, description="Max refinement iterations")
        ] = 3,
    ) -> str:
        """Execute a task through an orchestrator workflow.

        Routes the task through a sequence of AI agents (e.g. codex -> gemini -> claude)
        for implementation, review, and refinement.
        """
        orch = get_engine("orchestrator")

        if not task or not task.strip():
            raise ToolError("Task cannot be empty")
        if len(task) > 50000:
            raise ToolError("Task exceeds 50000 character limit")

        await ctx.info(
            f"Starting orchestrator workflow '{workflow}' with {max_iterations} max iterations"
        )

        try:
            result = orch.execute_task(
                task=task.strip(),
                workflow_name=workflow,
                max_iterations=max_iterations,
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"Execution failed: {exc}") from exc

        steps_summary = []
        for iteration in result.get("iterations", []):
            for step in iteration.get("steps", []):
                status = "OK" if step.get("success") else "FAIL"
                steps_summary.append(f"  [{status}] {step.get('agent')} ({step.get('task')})")

        return json.dumps(
            {
                "success": result.get("success"),
                "workflow": result.get("workflow"),
                "iterations": len(result.get("iterations", [])),
                "steps": steps_summary,
                "final_output": result.get("final_output", ""),
            },
            indent=2,
            default=str,
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def orchestrator_list_agents(ctx: Context) -> str:
        """List available orchestrator agents with their roles."""
        orch = get_engine("orchestrator")
        agents = []
        for name, _ in orch.adapters.items():
            cfg = orch.config.get("agents", {}).get(name, {})
            agents.append(
                {
                    "name": name,
                    "role": cfg.get("role", ""),
                    "type": cfg.get("type", "cli"),
                    "available": True,
                }
            )
        return json.dumps({"agents": agents, "count": len(agents)}, indent=2)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def orchestrator_list_workflows(ctx: Context) -> str:
        """List available workflows with their step sequences."""
        orch = get_engine("orchestrator")
        workflows = {}
        for name in orch.get_workflows():
            wf_config = orch.config.get("workflows", {}).get(name, [])
            steps = orch._extract_workflow_steps(wf_config)
            workflows[name] = [
                {"agent": s.get("agent"), "task": s.get("task") or s.get("role")} for s in steps
            ]
        return json.dumps({"workflows": workflows}, indent=2)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def orchestrator_health(ctx: Context) -> str:
        """Check orchestrator health: engine status, agent count, workflows."""
        orch = get_engine("orchestrator")
        return json.dumps(
            {
                "status": "healthy",
                "agents": len(orch.adapters),
                "agent_names": list(orch.adapters.keys()),
                "workflows": orch.get_workflows(),
                "offline_mode": orch.is_offline_mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
