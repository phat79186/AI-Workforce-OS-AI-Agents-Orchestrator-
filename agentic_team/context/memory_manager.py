"""
Memory Manager - High-level API for the agentic team context system.

Independent implementation — does NOT import from orchestrator/context.
Uses FTS5 (SQLite built-in) for search; no external embedding dependency.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from agentic_team.context.models.schemas import (
    ConversationNode,
    DecisionNode,
    Edge,
    EdgeType,
    MistakeNode,
    Node,
    NodeType,
    PatternNode,
    SearchResult,
    TaskNode,
)
from agentic_team.context.ops.analytics import ContextAnalytics
from agentic_team.context.ops.export import ContextExporter
from agentic_team.context.ops.pruning import ContextPruner
from agentic_team.context.search.bm25_index import BM25Index
from agentic_team.context.search.fts_search import FTSSearch
from agentic_team.context.store.graph_store import GraphStore


class MemoryManager:
    """High-level API for agentic team context management.

    Provides storage, search (BM25 + FTS5 hybrid), analytics,
    pruning, and export capabilities backed by an SQLite graph store.
    """

    def __init__(self, db_path: str | None = None):
        """Initialize the memory manager.

        Args:
            db_path: Path to database file. Defaults to ~/.agentic-team/context.db
        """
        self.logger = logging.getLogger("agentic_team.context.memory_manager")
        self.graph_store = GraphStore(db_path)
        self._bm25 = BM25Index(self.graph_store)
        self._fts = FTSSearch(self.graph_store)

    def store_conversation(
        self,
        messages: list[dict[str, str]],
        summary: str | None = None,
        session_id: str | None = None,
        participants: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            summary: Optional conversation summary.
            session_id: Optional session identifier.
            participants: List of participants (agents, users).
            tags: Optional tags for categorization.
            metadata: Additional metadata.

        Returns:
            Node ID.
        """
        content = "\n".join(f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in messages)

        node = ConversationNode(
            title=summary or f"Conversation ({len(messages)} messages)",
            content=content,
            messages=messages,
            summary=summary or "",
            session_id=session_id or str(uuid4()),
            participants=participants or [],
            tags=tags or ["conversation"],
            metadata=metadata or {},
        )

        self.graph_store.add_node(node)
        return node.id

    def store_task(
        self,
        task_description: str,
        outcome: str,
        success: bool,
        duration_ms: int = 0,
        agents_involved: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        project_id: str = "",
    ) -> str:
        """Store a completed task.

        Args:
            task_description: Description of the task.
            outcome: Task outcome/result.
            success: Whether task succeeded.
            duration_ms: Task duration in milliseconds.
            agents_involved: List of agents that participated.
            tags: Optional tags.
            metadata: Additional metadata.
            project_id: Optional project scope.

        Returns:
            Node ID.
        """
        status = "success" if success else "failed"

        node = TaskNode(
            title=f"Task: {task_description[:100]}",
            content=outcome,
            task_description=task_description,
            outcome=outcome,
            success=success,
            duration_ms=duration_ms,
            agents_involved=agents_involved or [],
            tags=tags or ["task", status],
            metadata=metadata or {},
            importance_score=1.5 if success else 2.0,
            project_id=project_id,
        )

        self.graph_store.add_node(node)
        return node.id

    def log_mistake(
        self,
        error_description: str,
        context: str = "",
        correction: str = "",
        prevention: str = "",
        category: str = "general",
        severity: str = "medium",
    ) -> str:
        """Log a mistake for future learning.

        Args:
            error_description: Description of the error.
            context: Context in which error occurred.
            correction: How the error was corrected.
            prevention: How to prevent this in future.
            category: Error category.
            severity: Error severity (low, medium, high, critical).

        Returns:
            Node ID.
        """
        node = MistakeNode(
            title=f"Mistake: {category}",
            content=f"{error_description}\n\nContext: {context}",
            error_type=category,
            error_message=error_description,
            context_description=context,
            correction=correction,
            prevention_strategy=prevention,
            severity=severity,
            tags=["mistake", category, severity],
            importance_score={"low": 1.0, "medium": 1.5, "high": 2.0, "critical": 3.0}.get(
                severity, 1.5
            ),
        )

        self.graph_store.add_node(node)
        return node.id

    def store_pattern(
        self,
        name: str,
        description: str,
        code_example: str = "",
        language: str = "",
        category: str = "general",
        tags: list[str] | None = None,
    ) -> str:
        """Store a code pattern.

        Args:
            name: Pattern name.
            description: Pattern description.
            code_example: Example code illustrating the pattern.
            language: Programming language.
            category: Pattern category.
            tags: Optional tags.

        Returns:
            Node ID.
        """
        node = PatternNode(
            title=name,
            content=description,
            pattern_name=name,
            pattern_type=category,
            description=description,
            examples=[code_example] if code_example else [],
            languages=[language] if language else [],
            tags=tags or ["pattern", category],
        )

        self.graph_store.add_node(node)
        return node.id

    def store_decision(
        self,
        title: str,
        description: str,
        rationale: str,
        alternatives: list[str] | None = None,
        chosen: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """Store an architectural decision.

        Args:
            title: Decision title.
            description: Decision description.
            rationale: Reasoning behind the decision.
            alternatives: Alternatives considered.
            chosen: The chosen approach.
            tags: Optional tags.

        Returns:
            Node ID.
        """
        node = DecisionNode(
            title=title,
            content=description,
            decision_title=title,
            decision_description=description,
            rationale=rationale,
            alternatives_considered=alternatives or [],
            trade_offs=chosen,
            tags=tags or ["decision"],
            importance_score=2.0,
        )

        self.graph_store.add_node(node)
        return node.id

    def search(
        self,
        query: str,
        limit: int = 20,
        node_types: list[NodeType] | None = None,
    ) -> list[SearchResult]:
        """Search the context graph using FTS5.

        Args:
            query: Search query.
            limit: Maximum results.
            node_types: Filter by node types.

        Returns:
            List of search results.
        """
        safe_query = self._sanitize_fts_query(query)
        if not safe_query:
            return []

        try:
            raw_results = self.graph_store.full_text_search(safe_query, limit=limit * 2)
        except Exception as e:
            self.logger.debug("FTS search failed for query '%s': %s", query, e)
            return []

        results: list[SearchResult] = []
        for node, score in raw_results:
            if node_types and node.node_type not in node_types:
                continue
            results.append(
                SearchResult(
                    node=node,
                    score=score,
                    match_type="fts5",
                )
            )
            if len(results) >= limit:
                break

        return results

    def get_relevant_context(
        self,
        task_description: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Get context relevant to a task description.

        Args:
            task_description: The task to find context for.
            limit: Maximum results.

        Returns:
            List of relevant search results.
        """
        return self.search(task_description, limit=limit)

    def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics.

        Returns:
            Dictionary with node/edge counts by type.
        """
        return self.graph_store.get_stats()

    def link_nodes(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a relationship between two nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Type of relationship.
            weight: Edge weight.
            metadata: Additional metadata.

        Returns:
            Edge ID.
        """
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            metadata=metadata or {},
        )
        return self.graph_store.add_edge(edge)

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        node_types: list[NodeType] | None = None,
    ) -> list[SearchResult]:
        """Search combining BM25 keyword and FTS5 results.

        Merges results from both engines, de-duplicates by node ID,
        and returns the top *limit* results by combined score.

        Args:
            query: Search query.
            limit: Maximum results.
            node_types: Optional filter by node types.

        Returns:
            List of search results.
        """
        score_map: dict[str, tuple[Node, float, str]] = {}

        bm25_results = self._bm25.search(query, limit=limit, node_types=node_types)
        for node, score in bm25_results:
            score_map[node.id] = (node, score, "bm25")

        fts_results = self._fts.search(query, limit=limit, node_types=node_types)
        for node, score in fts_results:
            if node.id in score_map:
                existing_node, existing_score, _ = score_map[node.id]
                score_map[node.id] = (existing_node, existing_score + score, "hybrid")
            else:
                score_map[node.id] = (node, score, "fts5")

        ranked = sorted(score_map.values(), key=lambda x: x[1], reverse=True)

        results: list[SearchResult] = []
        for node, score, match_type in ranked[:limit]:
            results.append(SearchResult(node=node, score=score, match_type=match_type))

        return results

    def get_analytics(self) -> ContextAnalytics:
        """Return a ContextAnalytics instance for this store.

        Returns:
            ContextAnalytics bound to the current graph store.
        """
        return ContextAnalytics(self.graph_store)

    def get_pruner(self) -> ContextPruner:
        """Return a ContextPruner instance for this store.

        Returns:
            ContextPruner bound to the current graph store.
        """
        return ContextPruner(self.graph_store)

    def get_exporter(self) -> ContextExporter:
        """Return a ContextExporter instance for this store.

        Returns:
            ContextExporter bound to the current graph store.
        """
        return ContextExporter(self.graph_store)

    # ------------------------------------------------------------------
    # Project-scoped operations
    # ------------------------------------------------------------------

    def register_project(self, project_path: str) -> str:
        """Register a project and perform an initial scan.

        Args:
            project_path: Path to the project root directory.

        Returns:
            Deterministic project_id.
        """
        from agentic_team.context.ops.project_scanner import ProjectScanner, generate_project_id

        pid = generate_project_id(project_path)

        existing = self.graph_store.query_nodes(node_type=NodeType.PROJECT, project_id=pid, limit=1)
        if existing:
            self.logger.info("Project already registered: %s (id=%s)", project_path, pid)
            return pid

        scanner = ProjectScanner(project_path)
        scan_result = scanner.scan()

        self.graph_store.add_node(scan_result["project_node"])
        for node in scan_result["file_nodes"]:
            self.graph_store.add_node(node)
        for node in scan_result["pattern_nodes"]:
            self.graph_store.add_node(node)
        for node in scan_result["decision_nodes"]:
            self.graph_store.add_node(node)
        for edge in scan_result["edges"]:
            self.graph_store.add_edge(edge)

        self.logger.info(
            "Project registered: %s — %d nodes, %d edges",
            project_path,
            (
                1
                + len(scan_result["file_nodes"])
                + len(scan_result["pattern_nodes"])
                + len(scan_result["decision_nodes"])
            ),
            len(scan_result["edges"]),
        )
        return pid

    def rescan_project(self, project_path: str) -> str:
        """Delete existing project graph and rebuild from scratch.

        Args:
            project_path: Project root directory.

        Returns:
            project_id
        """
        from agentic_team.context.ops.project_scanner import generate_project_id

        pid = generate_project_id(project_path)
        self.delete_project_graph(pid)
        return self.register_project(project_path)

    def delete_project_graph(self, project_id: str) -> int:
        """Remove all nodes (and cascading edges) for a project.

        Args:
            project_id: The project identifier.

        Returns:
            Number of nodes deleted.
        """
        deleted = self.graph_store.delete_nodes_by_project(project_id)
        self.logger.info("Deleted %d nodes for project %s", deleted, project_id)
        return deleted

    def get_project_context(
        self,
        project_id: str,
        task: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get context scoped to a specific project.

        Args:
            project_id: The project identifier.
            task: Optional task description to focus the search.
            limit: Maximum results per category.

        Returns:
            Categorised context dictionary.
        """
        context: dict[str, Any] = {
            "project": None,
            "patterns": [],
            "decisions": [],
            "tasks": [],
            "mistakes": [],
            "files": [],
        }

        project_nodes = self.graph_store.query_nodes(
            node_type=NodeType.PROJECT, project_id=project_id, limit=1
        )
        if project_nodes:
            context["project"] = project_nodes[0].to_dict()

        if task:
            results = self.search(task, limit=limit)
            for r in results:
                if r.node.project_id and r.node.project_id != project_id:
                    continue
                entry = r.to_dict()
                nt = r.node.node_type
                if nt == NodeType.PATTERN:
                    context["patterns"].append(entry)
                elif nt == NodeType.DECISION:
                    context["decisions"].append(entry)
                elif nt == NodeType.TASK:
                    context["tasks"].append(entry)
                elif nt == NodeType.MISTAKE:
                    context["mistakes"].append(entry)
                elif nt == NodeType.FILE:
                    context["files"].append(entry)
        else:
            for nt_key, nt_val in [
                ("patterns", NodeType.PATTERN),
                ("decisions", NodeType.DECISION),
                ("files", NodeType.FILE),
            ]:
                nodes = self.graph_store.query_nodes(
                    node_type=nt_val, project_id=project_id, limit=limit
                )
                context[nt_key] = [n.to_dict() for n in nodes]

        return context

    def close(self) -> None:
        """Close the memory manager."""
        self.graph_store.close()

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """Sanitize a query string for FTS5 MATCH syntax.

        Wraps each word in double quotes to avoid FTS5 syntax errors
        from special characters.

        Args:
            query: Raw query string.

        Returns:
            Sanitized query safe for FTS5 MATCH.
        """
        words = query.split()
        if not words:
            return ""
        safe_words = [f'"{w.replace(chr(34), "")}"' for w in words if w.strip()]
        return " ".join(safe_words)
