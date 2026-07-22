"""Organizational Memory combining Obsidian Vault, Vector RAG, Memory Graphs, and Cross-Project Organizational Learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from shared_knowledge import KnowledgeBridge


@dataclass
class OrganizationalLearningRecord:
    """Represents a corporate memory record storing cross-project organizational learnings."""

    project_name: str
    lessons_learned: List[str] = field(default_factory=list)
    architecture_decisions: List[str] = field(default_factory=list)
    security_findings: List[str] = field(default_factory=list)
    failed_approaches: List[str] = field(default_factory=list)
    successful_patterns: List[str] = field(default_factory=list)
    scope: str = "ORGANIZATION"


class OrganizationalMemory:
    """Enterprise Organizational Memory storing corporate ADRs, research, and cross-project organizational learnings."""

    def __init__(self, vault_path: Optional[str] = None) -> None:
        self.bridge = KnowledgeBridge(vault_path=vault_path)
        self._learning_history: List[OrganizationalLearningRecord] = []

    def record_decision(self, title: str, decision: str, category: str = "Corporate_ADR", scope: str = "ORGANIZATION") -> Optional[str]:
        """Record an architectural or strategic decision into corporate Obsidian Vault."""
        return self.bridge.publish_research(title=title, content=decision, category=category, scope=scope)

    def save_project_learnings(self, record: OrganizationalLearningRecord) -> Optional[str]:
        """Save project completion learnings into Real Obsidian Vault for future initiatives to consult."""
        self._learning_history.append(record)

        content = (
            f"# Organizational Learning Summary: {record.project_name}\n\n"
            f"## Lessons Learned\n" + "\n".join(f"- {item}" for item in record.lessons_learned) + "\n\n"
            f"## Architecture Decisions (ADRs)\n" + "\n".join(f"- {item}" for item in record.architecture_decisions) + "\n\n"
            f"## Security Findings\n" + "\n".join(f"- {item}" for item in record.security_findings) + "\n\n"
            f"## Failed Approaches Avoided\n" + "\n".join(f"- {item}" for item in record.failed_approaches) + "\n\n"
            f"## Successful Patterns\n" + "\n".join(f"- {item}" for item in record.successful_patterns)
        )

        return self.bridge.publish_research(
            title=f"Learnings_{record.project_name.replace(' ', '_')}",
            content=content,
            category="Organizational_Learnings",
            scope=record.scope,
            tags=["organizational_memory", "lessons_learned"],
        )

    def get_lessons_learned(self, query: str = "", scope: Optional[str] = "ORGANIZATION") -> List[Dict[str, Any]]:
        """Retrieve historical organizational lessons learned when starting a new project."""
        if not query:
            query = "Organizational Lessons Learned ADR Architecture Security"
        return self.bridge.retrieve_context_for_agent(query, top_k=5, scope=scope)
