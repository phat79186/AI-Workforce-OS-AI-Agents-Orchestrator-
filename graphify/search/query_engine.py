"""
Graph query engine — structural queries over the project graph.

Provides traversal, relationship queries, dependency analysis,
path finding, god node detection, and aggregation.
"""

from __future__ import annotations

import logging
from typing import Any

from graphify.core.graph import GraphStore
from graphify.core.schema import EdgeType, Node, NodeType

logger = logging.getLogger(__name__)


class QueryEngine:
    """High-level query interface for the project graph."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def get_file_structure(self, file_path: str, project_id: str = "") -> dict[str, Any]:
        """Return the full node tree for a single file."""
        file_nodes = self._store.get_nodes(
            project_id=project_id,
            node_type=NodeType.FILE,
        )
        file_node = next((n for n in file_nodes if n.file_path == file_path), None)
        if not file_node:
            return {}

        children = self._store.get_neighbors(
            file_node.id, direction="outgoing", edge_type=EdgeType.CONTAINS
        )

        return {
            "file": self._node_to_dict(file_node),
            "children": [
                {
                    "node": self._node_to_dict(n),
                    "edge": e.edge_type.value,
                    "sub_children": [
                        self._node_to_dict(sub_n)
                        for sub_n, _ in self._store.get_neighbors(
                            n.id,
                            direction="outgoing",
                            edge_type=EdgeType.CONTAINS,
                        )
                    ],
                }
                for n, e in children
            ],
        }

    def get_dependencies(self, project_id: str = "") -> list[dict[str, Any]]:
        """List all external dependencies for a project."""
        deps = self._store.get_nodes(project_id=project_id, node_type=NodeType.DEPENDENCY)
        return [self._node_to_dict(d) for d in deps]

    def get_imports_for_file(self, file_path: str, project_id: str = "") -> list[dict[str, Any]]:
        """List imports for a specific file."""
        imports = self._store.get_nodes(project_id=project_id, node_type=NodeType.IMPORT)
        return [self._node_to_dict(n) for n in imports if n.file_path == file_path]

    def get_class_hierarchy(self, project_id: str = "") -> list[dict[str, Any]]:
        """Build class inheritance tree."""
        classes = self._store.get_nodes(project_id=project_id, node_type=NodeType.CLASS)
        hierarchy = []

        for cls in classes:
            parents = self._store.get_neighbors(
                cls.id,
                direction="outgoing",
                edge_type=EdgeType.INHERITS,
            )
            children = self._store.get_neighbors(
                cls.id,
                direction="incoming",
                edge_type=EdgeType.INHERITS,
            )
            hierarchy.append(
                {
                    "class": self._node_to_dict(cls),
                    "inherits_from": [self._node_to_dict(n) for n, _ in parents],
                    "inherited_by": [self._node_to_dict(n) for n, _ in children],
                }
            )

        return hierarchy

    def get_tests(self, project_id: str = "") -> list[dict[str, Any]]:
        """List all test nodes."""
        tests = self._store.get_nodes(project_id=project_id, node_type=NodeType.TEST)
        return [self._node_to_dict(t) for t in tests]

    # ------------------------------------------------------------------
    # Subgraph extraction
    # ------------------------------------------------------------------

    def get_subgraph(
        self,
        root_id: str,
        max_depth: int = 3,
        edge_types: list[EdgeType] | None = None,
    ) -> dict[str, Any]:
        """Extract a subgraph rooted at a node up to max_depth hops."""
        visited: set[str] = set()
        nodes_out: list[dict[str, Any]] = []
        edges_out: list[dict[str, Any]] = []

        queue = [(root_id, 0)]
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)

            node = self._store.get_node(node_id)
            if node:
                nodes_out.append(self._node_to_dict(node))

            for et in edge_types or list(EdgeType):
                for neighbor, edge in self._store.get_neighbors(node_id, "outgoing", et):
                    edges_out.append(
                        {
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "type": edge.edge_type.value,
                        }
                    )
                    if neighbor.id not in visited:
                        queue.append((neighbor.id, depth + 1))

        return {"nodes": nodes_out, "edges": edges_out}

    # ------------------------------------------------------------------
    # Aggregations
    # ------------------------------------------------------------------

    def language_breakdown(self, project_id: str = "") -> dict[str, int]:
        """Count files per language."""
        files = self._store.get_nodes(project_id=project_id, node_type=NodeType.FILE, limit=10_000)
        breakdown: dict[str, int] = {}
        for f in files:
            lang = f.language or "unknown"
            breakdown[lang] = breakdown.get(lang, 0) + 1
        return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))

    def complexity_hotspots(self, project_id: str = "", top_n: int = 20) -> list[dict[str, Any]]:
        """Find files with the most classes + functions (complexity proxy)."""
        files = self._store.get_nodes(project_id=project_id, node_type=NodeType.FILE, limit=10_000)
        scored = []
        for f in files:
            children = self._store.get_neighbors(f.id, "outgoing", EdgeType.CONTAINS)
            class_count = sum(1 for n, _ in children if n.node_type == NodeType.CLASS)
            func_count = sum(1 for n, _ in children if n.node_type == NodeType.FUNCTION)
            test_count = sum(1 for n, _ in children if n.node_type == NodeType.TEST)
            lines = f.metadata.get("line_count", 0)
            score = class_count * 3 + func_count + lines / 100
            scored.append(
                {
                    "file": f.file_path,
                    "classes": class_count,
                    "functions": func_count,
                    "tests": test_count,
                    "lines": lines,
                    "score": round(score, 1),
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    def summary(self, project_id: str = "") -> dict[str, Any]:
        """Return a complete project summary from the graph."""
        stats = self._store.stats(project_id)
        meta = self._store.get_project_meta(project_id)
        return {
            "project_id": project_id,
            "name": meta.name if meta else "",
            "root_path": meta.root_path if meta else "",
            **stats,
            "languages": self.language_breakdown(project_id),
        }

    # ------------------------------------------------------------------
    # Path finding
    # ------------------------------------------------------------------

    def _resolve_name(self, name: str, project_id: str = "") -> Node | None:
        """Resolve a human-readable name to a node via direct SQL lookup."""
        conn = self._store._get_conn()  # noqa: SLF001
        clause = "WHERE (name = ? OR qualified_name = ?)"
        params: list[Any] = [name, name]
        if project_id:
            clause += " AND project_id = ?"
            params.append(project_id)
        row = conn.execute(
            f"SELECT * FROM nodes {clause} LIMIT 1",
            params,
        ).fetchone()
        if row:
            return self._store._row_to_node(row)  # noqa: SLF001
        return None

    def find_path(
        self,
        start_name: str,
        end_name: str,
        project_id: str = "",
    ) -> list[dict[str, Any]]:
        """Find shortest path between two named nodes."""
        start = self._resolve_name(start_name, project_id)
        end = self._resolve_name(end_name, project_id)
        if not start or not end:
            return []

        path_ids = self._store.shortest_path(start.id, end.id)
        if not path_ids:
            return []

        result = []
        for nid in path_ids:
            node = self._store.get_node(nid)
            if node:
                result.append(self._node_to_dict(node))
        return result

    # ------------------------------------------------------------------
    # Node explanation
    # ------------------------------------------------------------------

    def explain_node(self, name: str, project_id: str = "") -> dict[str, Any]:
        """Explain a node: what it is, what it connects to, and why it matters."""
        target = self._resolve_name(name, project_id)
        if not target:
            return {"error": f"Node '{name}' not found"}

        degree = self._store.node_degree(target.id)
        outgoing = self._store.get_neighbors(target.id, "outgoing")
        incoming = self._store.get_neighbors(target.id, "incoming")

        return {
            "node": self._node_to_dict(target),
            "degree": degree,
            "outgoing": [
                {
                    "node": self._node_to_dict(n),
                    "edge_type": e.edge_type.value,
                    "confidence": e.confidence,
                }
                for n, e in outgoing
            ],
            "incoming": [
                {
                    "node": self._node_to_dict(n),
                    "edge_type": e.edge_type.value,
                    "confidence": e.confidence,
                }
                for n, e in incoming
            ],
        }

    # ------------------------------------------------------------------
    # Community detection (lightweight label propagation)
    # ------------------------------------------------------------------

    def detect_communities(
        self,
        project_id: str = "",
        iterations: int = 10,
    ) -> dict[str, list[dict[str, Any]]]:
        """Simple label propagation community detection.

        Returns ``{community_label: [node_dicts]}``.
        """
        nodes = self._store.get_nodes(
            project_id=project_id,
            limit=10_000,
        )
        # Skip structural nodes for community detection
        code_nodes = [
            n
            for n in nodes
            if n.node_type
            not in (
                NodeType.PROJECT,
                NodeType.DIRECTORY,
                NodeType.COMMUNITY,
            )
        ]
        if not code_nodes:
            return {}

        # Initialize: each node is its own community
        labels: dict[str, str] = {n.id: n.id for n in code_nodes}
        node_set = set(labels.keys())

        for _ in range(iterations):
            changed = False
            for n in code_nodes:
                neighbors = self._store.get_neighbors(n.id, "outgoing")
                neighbors += self._store.get_neighbors(n.id, "incoming")

                neighbor_labels: dict[str, float] = {}
                for nbr, edge in neighbors:
                    if nbr.id in node_set:
                        lbl = labels.get(nbr.id, nbr.id)
                        neighbor_labels[lbl] = neighbor_labels.get(lbl, 0) + edge.weight

                if neighbor_labels:
                    best_label = max(neighbor_labels, key=neighbor_labels.get)
                    if labels[n.id] != best_label:
                        labels[n.id] = best_label
                        changed = True

            if not changed:
                break

        # Group by community
        communities: dict[str, list[dict[str, Any]]] = {}
        node_map = {n.id: n for n in code_nodes}
        for node_id, community_label in labels.items():
            node = node_map.get(node_id)
            if node:
                communities.setdefault(community_label, []).append(
                    self._node_to_dict(node),
                )

        return communities

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_to_dict(node: Node) -> dict[str, Any]:
        """Serialize a Node to a JSON-friendly dict."""
        return {
            "id": node.id,
            "type": node.node_type.value,
            "name": node.name,
            "qualified_name": node.qualified_name,
            "file_path": node.file_path,
            "language": node.language,
            "line_start": node.line_start,
            "line_end": node.line_end,
            "metadata": node.metadata,
        }
