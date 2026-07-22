"""Layer 3: Tool Router (DO WITH WHAT?) - Grants and routes authorized tools to agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolRouteResult:
    """Selection result from Tool Router."""

    allowed_tools: List[str] = field(default_factory=list)
    restricted_tools: List[str] = field(default_factory=list)
    rationale: str = ""


class ToolRouter:
    """Tool Router enforcing least-privilege tool access per agent role."""

    ROLE_TOOL_MAP = {
        "Coding Agent": ["file_system", "git", "terminal", "test_runner"],
        "Testing Agent": ["terminal", "test_runner", "file_system"],
        "Debugging Agent": ["terminal", "file_system", "git", "test_runner"],
        "Research Agent": ["browser", "rag", "obsidian", "file_system"],
        "RAG/Knowledge Agent": ["rag", "obsidian", "file_system"],
        "Code Review Agent": ["git", "file_system"],
        "Security Review Agent": ["git", "file_system", "security_scanner"],
        "Documentation Agent": ["obsidian", "file_system"],
    }

    def route(self, agent_role: str) -> ToolRouteResult:
        """Route allowed tools for a given agent role."""
        allowed = self.ROLE_TOOL_MAP.get(agent_role, ["file_system"])
        return ToolRouteResult(
            allowed_tools=allowed,
            restricted_tools=["db_drop", "force_push", "deploy_prod"],
            rationale=f"Granted permissions for {agent_role}",
        )
