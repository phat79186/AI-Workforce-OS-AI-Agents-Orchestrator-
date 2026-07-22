"""Layer 1: Agent Router (WHO?) - Selects appropriate specialized AI Agent for a given subtask."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AgentRouteResult:
    """Selection result from Agent Router."""

    agent_role: str
    rationale: str
    confidence: float = 1.0


class AgentRouter:
    """Agent Router mapping task descriptions to specialized agent roles."""

    AGENT_MAP = {
        "code": "Coding Agent",
        "implement": "Coding Agent",
        "feature": "Coding Agent",
        "fix": "Coding Agent",
        "refactor": "Coding Agent",
        "test": "Testing Agent",
        "unit": "Testing Agent",
        "integration": "Testing Agent",
        "review": "Code Review Agent",
        "audit": "Security Review Agent",
        "security": "Security Review Agent",
        "vulnerability": "Security Review Agent",
        "doc": "Documentation Agent",
        "readme": "Documentation Agent",
        "debug": "Debugging Agent",
        "error": "Debugging Agent",
        "fail": "Debugging Agent",
        "research": "Research Agent",
        "search": "Research Agent",
        "rag": "RAG/Knowledge Agent",
        "knowledge": "RAG/Knowledge Agent",
        "vault": "RAG/Knowledge Agent",
    }

    def route(self, task_description: str, metadata: Optional[Dict[str, Any]] = None) -> AgentRouteResult:
        """Route task description to the most appropriate agent role."""
        desc_lower = task_description.lower()

        # Sort keywords by length descending so specific keywords match before generic ones like 'code'
        sorted_map = sorted(self.AGENT_MAP.items(), key=lambda kv: len(kv[0]), reverse=True)
        for keyword, role in sorted_map:
            if keyword in desc_lower:
                return AgentRouteResult(
                    agent_role=role,
                    rationale=f"Matched keyword '{keyword}' in task description",
                    confidence=0.9,
                )

        # Default fallback role
        return AgentRouteResult(
            agent_role="Coding Agent",
            rationale="Default fallback for software task",
            confidence=0.5,
        )
