"""Base Domain class for Layer 2 Domain Ecosystems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DomainMetadata:
    """Metadata for domain department registration."""

    name: str
    description: str
    roles: List[str] = field(default_factory=list)
    workflows: List[str] = field(default_factory=list)


class BaseDomain:
    """Abstract Base Class for Domain Departments."""

    def __init__(self, metadata: DomainMetadata) -> None:
        self.metadata = metadata

    def get_workflows(self) -> List[str]:
        """Return available domain workflows."""
        return self.metadata.workflows

    def get_roles(self) -> List[str]:
        """Return available domain roles."""
        return self.metadata.roles
