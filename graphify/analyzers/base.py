"""
Base analyzer interface for all language analyzers.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

from graphify.core.schema import Edge, Node


@dataclass
class AnalysisResult:
    """Container for analyzer output."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)


class BaseAnalyzer(abc.ABC):
    """Abstract base for language-specific analyzers."""

    @abc.abstractmethod
    def analyze(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        """Analyze source code and return extracted nodes and edges.

        Args:
            source: Full file content.
            file_path: Relative path within the project.
            file_node_id: ID of the parent FILE node.
            project_id: Project scope identifier.

        Returns:
            AnalysisResult with discovered nodes and edges.
        """
