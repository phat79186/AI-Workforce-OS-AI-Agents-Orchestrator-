"""
Schema definitions for Agentic Team Context nodes and edges.

Independent implementation — does NOT import from orchestrator/context.
Defines the core data structures for the persistent memory system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class NodeType(str, Enum):
    """Types of nodes in the context graph."""

    CONVERSATION = "conversation"
    TASK = "task"
    MISTAKE = "mistake"
    PATTERN = "pattern"
    DECISION = "decision"
    CODE_SNIPPET = "code_snippet"
    PREFERENCE = "preference"
    FILE = "file"
    CONCEPT = "concept"
    AGENT_OUTPUT = "agent_output"
    PROJECT = "project"


class EdgeType(str, Enum):
    """Types of edges (relationships) in the context graph."""

    RELATED_TO = "related_to"
    CAUSED_BY = "caused_by"
    FIXED_BY = "fixed_by"
    SIMILAR_TO = "similar_to"
    DEPENDS_ON = "depends_on"
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"
    LEARNED_FROM = "learned_from"
    REFERENCES = "references"
    CONTAINS = "contains"
    PRODUCED_BY = "produced_by"
    USED_IN = "used_in"


@dataclass
class Node:
    """Base node in the context graph."""

    id: str = field(default_factory=lambda: str(uuid4()))
    node_type: NodeType = NodeType.CONCEPT
    content: str = ""
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: list[float] | None = None
    importance_score: float = 1.0
    project_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "content": self.content,
            "title": self.title,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "embedding": self.embedding,
            "importance_score": self.importance_score,
            "project_id": self.project_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        """Create node from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            node_type=NodeType(data.get("node_type", "concept")),
            content=data.get("content", ""),
            title=data.get("title", ""),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(timezone.utc)
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now(timezone.utc)
            ),
            embedding=data.get("embedding"),
            importance_score=data.get("importance_score", 1.0),
            project_id=data.get("project_id", ""),
        )


@dataclass
class Edge:
    """Edge (relationship) between nodes in the context graph."""

    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.RELATED_TO
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert edge to dictionary for storage."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """Create edge from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            edge_type=EdgeType(data.get("edge_type", "related_to")),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(timezone.utc)
            ),
        )


@dataclass
class ConversationNode(Node):
    """Node representing a conversation or chat session."""

    node_type: NodeType = field(default=NodeType.CONVERSATION)
    messages: list[dict[str, str]] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    session_id: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "messages": self.messages,
                "participants": self.participants,
                "session_id": self.session_id,
                "summary": self.summary,
            }
        )
        return data


@dataclass
class TaskNode(Node):
    """Node representing a completed task."""

    node_type: NodeType = field(default=NodeType.TASK)
    task_description: str = ""
    outcome: str = ""
    success: bool = True
    duration_ms: int = 0
    workflow_used: str = ""
    agents_involved: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "task_description": self.task_description,
                "outcome": self.outcome,
                "success": self.success,
                "duration_ms": self.duration_ms,
                "workflow_used": self.workflow_used,
                "agents_involved": self.agents_involved,
                "files_modified": self.files_modified,
            }
        )
        return data


@dataclass
class MistakeNode(Node):
    """Node representing an error or mistake made."""

    node_type: NodeType = field(default=NodeType.MISTAKE)
    error_type: str = ""
    error_message: str = ""
    context_description: str = ""
    correction: str = ""
    prevention_strategy: str = ""
    severity: str = "medium"
    occurrence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "error_type": self.error_type,
                "error_message": self.error_message,
                "context_description": self.context_description,
                "correction": self.correction,
                "prevention_strategy": self.prevention_strategy,
                "severity": self.severity,
                "occurrence_count": self.occurrence_count,
            }
        )
        return data


@dataclass
class PatternNode(Node):
    """Node representing a recognized code or behavior pattern."""

    node_type: NodeType = field(default=NodeType.PATTERN)
    pattern_name: str = ""
    pattern_type: str = ""
    description: str = ""
    examples: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "pattern_name": self.pattern_name,
                "pattern_type": self.pattern_type,
                "description": self.description,
                "examples": self.examples,
                "anti_patterns": self.anti_patterns,
                "languages": self.languages,
                "frameworks": self.frameworks,
            }
        )
        return data


@dataclass
class DecisionNode(Node):
    """Node representing an architectural or design decision."""

    node_type: NodeType = field(default=NodeType.DECISION)
    decision_title: str = ""
    decision_description: str = ""
    rationale: str = ""
    alternatives_considered: list[str] = field(default_factory=list)
    trade_offs: str = ""
    status: str = "accepted"
    stakeholders: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "decision_title": self.decision_title,
                "decision_description": self.decision_description,
                "rationale": self.rationale,
                "alternatives_considered": self.alternatives_considered,
                "trade_offs": self.trade_offs,
                "status": self.status,
                "stakeholders": self.stakeholders,
            }
        )
        return data


@dataclass
class CodeSnippetNode(Node):
    """Node representing a useful code snippet."""

    node_type: NodeType = field(default=NodeType.CODE_SNIPPET)
    code: str = ""
    language: str = ""
    purpose: str = ""
    source_file: str = ""
    line_range: str = ""
    usage_count: int = 0
    quality_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "code": self.code,
                "language": self.language,
                "purpose": self.purpose,
                "source_file": self.source_file,
                "line_range": self.line_range,
                "usage_count": self.usage_count,
                "quality_score": self.quality_score,
            }
        )
        return data


@dataclass
class PreferenceNode(Node):
    """Node representing a learned user preference."""

    node_type: NodeType = field(default=NodeType.PREFERENCE)
    preference_key: str = ""
    preference_value: str = ""
    category: str = ""
    confidence: float = 1.0
    learned_from: str = ""
    times_applied: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary for storage."""
        data = super().to_dict()
        data.update(
            {
                "preference_key": self.preference_key,
                "preference_value": self.preference_value,
                "category": self.category,
                "confidence": self.confidence,
                "learned_from": self.learned_from,
                "times_applied": self.times_applied,
            }
        )
        return data


@dataclass
class ProjectNode(Node):
    """Node representing a registered user project."""

    node_type: NodeType = field(default=NodeType.PROJECT)
    project_path: str = ""
    project_name: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    description: str = ""
    file_count: int = 0
    last_scanned: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert node to dictionary representation."""
        data = super().to_dict()
        data.update(
            {
                "project_path": self.project_path,
                "project_name": self.project_name,
                "languages": self.languages,
                "frameworks": self.frameworks,
                "description": self.description,
                "file_count": self.file_count,
                "last_scanned": self.last_scanned,
            }
        )
        return data


@dataclass
class SearchResult:
    """Result from a context search operation."""

    node: Node
    score: float
    match_type: str
    highlights: list[str] = field(default_factory=list)
    related_edges: list[Edge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "node": self.node.to_dict(),
            "score": self.score,
            "match_type": self.match_type,
            "highlights": self.highlights,
            "related_edges": [e.to_dict() for e in self.related_edges],
        }
