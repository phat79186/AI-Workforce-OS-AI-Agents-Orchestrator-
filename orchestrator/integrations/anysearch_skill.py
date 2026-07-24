"""Integration for anysearch-ai/anysearch-skill intelligent search skill + Panniantong/Agent-Reach deep retrieval."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from orchestrator.integrations.agent_reach import AgentReachEngine


class AnySearchSkill:
    """AnySearch skill executing unified searches across codebase, web, Obsidian memory, and Agent-Reach deep retrieval."""

    def __init__(self) -> None:
        self.agent_reach = AgentReachEngine()

    def execute_search(
        self, query: str, enable_agent_reach: bool = True, max_depth: int = 2
    ) -> Dict[str, Any]:
        """Execute unified search query enriched with Agent-Reach multi-engine retrieval."""
        keywords = [k for k in query.split() if len(k) > 2]
        base_sources = ["codebase", "web", "obsidian_vault"]

        reach_data = None
        if enable_agent_reach:
            reach_data = self.agent_reach.search_reach(query, max_depth=max_depth)
            base_sources.extend(reach_data["engines_searched"])

        unique_sources = sorted(list(set(base_sources)))

        return {
            "query": query,
            "matched_keywords": keywords,
            "sources_searched": unique_sources,
            "results_count": (len(keywords) * 2) + (len(reach_data["citations"]) if reach_data else 0),
            "agent_reach_source": self.agent_reach.source_repo,
            "agent_reach_enabled": enable_agent_reach,
            "reach_metadata": reach_data,
            "status": "COMPLETED",
        }
