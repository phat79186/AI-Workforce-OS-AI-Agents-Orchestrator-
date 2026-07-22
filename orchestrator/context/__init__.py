"""
Graph Context Base - Enterprise-grade persistent memory system for AI agents.

Sub-packages:
  models/  - Node, Edge, and type definitions
  store/   - SQLite-backed graph database
  search/  - BM25, semantic, hybrid, and advanced search
  ops/     - Analytics, pruning, export, versioning
"""

import sys

from orchestrator.context.memory_manager import MemoryManager
from orchestrator.context.models import schemas  # noqa: F401
from orchestrator.context.models import (
    CodeSnippetNode,
    ConversationNode,
    DecisionNode,
    Edge,
    EdgeType,
    MistakeNode,
    Node,
    NodeType,
    PatternNode,
    PreferenceNode,
    ProjectNode,
    TaskNode,
)
from orchestrator.context.ops import (  # noqa: F401
    ContextAnalytics,
    ContextExporter,
    ContextPruner,
    ContextVersioning,
    analytics,
    export,
    pruning,
    versioning,
)
from orchestrator.context.search import (  # noqa: F401
    AdvancedSearch,
    advanced_search,
    bm25_index,
    embeddings,
    hybrid_search,
)
from orchestrator.context.store import graph_store  # noqa: F401
from orchestrator.context.store import GraphStore

# Backward-compatible module aliases so old import paths still resolve.
# e.g. ``from orchestrator.context.schemas import Node`` keeps working.
sys.modules["orchestrator.context.schemas"] = schemas
sys.modules["orchestrator.context.graph_store"] = graph_store
sys.modules["orchestrator.context.bm25_index"] = bm25_index
sys.modules["orchestrator.context.embeddings"] = embeddings
sys.modules["orchestrator.context.hybrid_search"] = hybrid_search
sys.modules["orchestrator.context.advanced_search"] = advanced_search
sys.modules["orchestrator.context.analytics"] = analytics
sys.modules["orchestrator.context.pruning"] = pruning
sys.modules["orchestrator.context.export"] = export
sys.modules["orchestrator.context.versioning"] = versioning

__all__ = [
    "AdvancedSearch",
    "CodeSnippetNode",
    "ContextAnalytics",
    "ContextExporter",
    "ContextPruner",
    "ContextVersioning",
    "ConversationNode",
    "DecisionNode",
    "Edge",
    "EdgeType",
    "GraphStore",
    "MemoryManager",
    "MistakeNode",
    "Node",
    "NodeType",
    "PatternNode",
    "PreferenceNode",
    "ProjectNode",
    "TaskNode",
]
