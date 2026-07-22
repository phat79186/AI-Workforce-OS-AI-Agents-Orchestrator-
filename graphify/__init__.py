"""
Graphify — Turn any project directory into a queryable context graph.

Standalone system that scans codebases, extracts structure and relationships,
and builds a persistent SQLite-backed graph for AI agent context retrieval.
"""

from __future__ import annotations

__version__ = "1.1.0"
__all__ = [
    "Graphify",
    "GraphifyConfig",
    "GraphStore",
    "NodeType",
    "EdgeType",
    "EdgeProvenance",
    "GraphifyError",
    "ScanMetrics",
    "Scanner",
]

from graphify.core.config import GraphifyConfig  # noqa: E402
from graphify.core.exceptions import GraphifyError  # noqa: E402
from graphify.core.graph import GraphStore  # noqa: E402
from graphify.core.metrics import ScanMetrics  # noqa: E402
from graphify.core.scanner import Scanner  # noqa: E402
from graphify.core.schema import EdgeProvenance, EdgeType, NodeType  # noqa: E402


def Graphify(path: str, **kwargs) -> GraphStore:  # noqa: N802
    """Convenience factory: scan a project and return its graph store."""
    from graphify.cli import build_graph  # pylint: disable=C0415

    return build_graph(path, **kwargs)
