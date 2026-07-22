"""Integration for mattpocock/skills AI Agent Skill Framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MattPocockSkill:
    """Represents a skill from mattpocock/skills framework."""

    name: str
    description: str
    category: str
    instructions: str
    tags: List[str] = field(default_factory=list)


class MattPocockSkillsEngine:
    """Skill discovery and execution engine for mattpocock/skills framework."""

    def __init__(self) -> None:
        self._registry: Dict[str, MattPocockSkill] = {}
        self._register_default_skills()

    def _register_default_skills(self) -> None:
        """Register built-in skills from mattpocock/skills library."""
        self.register_skill(
            MattPocockSkill(
                name="typescript-pro",
                description="Advanced TypeScript type engineering, generics, and strict mode compliance.",
                category="development",
                instructions="Apply strict TypeScript types, avoid 'any', use utility types (Pick, Omit, Partial).",
                tags=["typescript", "frontend", "type-safety"],
            )
        )
        self.register_skill(
            MattPocockSkill(
                name="react-state-architecture",
                description="Best practices for React state management, hooks, and performance optimization.",
                category="development",
                instructions="Keep transient state local, use atomic state structures, avoid unnecessary re-renders.",
                tags=["react", "state", "ui"],
            )
        )

    def register_skill(self, skill: MattPocockSkill) -> None:
        """Register a new skill into the mattpocock skills registry."""
        self._registry[skill.name.lower()] = skill

    def find_skill(self, name_or_tag: str) -> Optional[MattPocockSkill]:
        """Find a skill by name or tag."""
        target = name_or_tag.lower()
        if target in self._registry:
            return self._registry[target]

        for s in self._registry.values():
            if any(target in t.lower() for t in s.tags):
                return s
        return None

    def list_skills(self) -> List[MattPocockSkill]:
        """List all registered skills."""
        return list(self._registry.values())
