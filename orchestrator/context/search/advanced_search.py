"""Advanced Search - Complex query capabilities for the context graph."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from orchestrator.context.store.graph_store import GraphStore


class AdvancedSearch:
    """Advanced search and graph query capabilities."""

    def __init__(self, graph_store: GraphStore):
        """Initialize advanced search.

        Args:
            graph_store: Graph store instance
        """
        self.logger = logging.getLogger("context.advanced_search")
        self.graph_store = graph_store

    def search_temporal(
        self,
        start_date: str,
        end_date: str,
        node_types: list[str] | None = None,
    ) -> list[dict]:
        """Search nodes within a time range.

        Args:
            start_date: Start date in ISO 8601 format
            end_date: End date in ISO 8601 format
            node_types: Optional list of node types to filter

        Returns:
            List of matching nodes as dicts
        """
        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = (
                    f"SELECT * FROM nodes WHERE created_at >= ? AND created_at <= ? "  # noqa: B608
                    f"AND node_type IN ({placeholders}) ORDER BY created_at DESC"
                )
                params: list[Any] = [start_date, end_date] + node_types
            else:
                query = (
                    "SELECT * FROM nodes WHERE created_at >= ? AND created_at <= ? "
                    "ORDER BY created_at DESC"
                )
                params = [start_date, end_date]

            cursor.execute(query, params)
            return [self.graph_store._row_to_node(row).to_dict() for row in cursor.fetchall()]

    def search_by_tags(
        self,
        tags: list[str],
        match_all: bool = True,
    ) -> list[dict]:
        """Search nodes by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, node must have all tags; if False, any tag matches

        Returns:
            List of matching nodes as dicts
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("SELECT * FROM nodes ORDER BY created_at DESC")
            results = []
            for row in cursor.fetchall():
                node = self.graph_store._row_to_node(row)
                node_tags = set(node.tags)
                search_tags = set(tags)

                if match_all:
                    if search_tags.issubset(node_tags):
                        results.append(node.to_dict())
                else:
                    if search_tags & node_tags:
                        results.append(node.to_dict())

        return results

    def get_neighbors(
        self,
        node_id: str,
        edge_types: list[str] | None = None,
        depth: int = 1,
    ) -> dict:
        """Multi-hop graph traversal from a starting node.

        Args:
            node_id: Starting node ID
            edge_types: Optional list of edge type strings to filter
            depth: Maximum traversal depth

        Returns:
            Dict with discovered nodes and edges
        """
        visited_nodes: dict[str, dict] = {}
        discovered_edges: list[dict] = []
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            current_id, current_depth = queue.popleft()

            if current_id in visited_nodes or current_depth > depth:
                continue

            node = self.graph_store.get_node(current_id)
            if node is None:
                continue

            visited_nodes[current_id] = node.to_dict()

            if current_depth < depth:
                with self.graph_store._transaction() as cursor:
                    cursor.execute(
                        "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
                        (current_id, current_id),
                    )
                    for row in cursor.fetchall():
                        edge = self.graph_store._row_to_edge(row)
                        if edge_types and edge.edge_type.value not in edge_types:
                            continue

                        discovered_edges.append(edge.to_dict())
                        neighbor_id = (
                            edge.target_id if edge.source_id == current_id else edge.source_id
                        )
                        if neighbor_id not in visited_nodes:
                            queue.append((neighbor_id, current_depth + 1))

        return {
            "nodes": list(visited_nodes.values()),
            "edges": discovered_edges,
        }

    def get_shortest_path(
        self,
        source_id: str,
        target_id: str,
    ) -> list[dict] | None:
        """Find shortest path between two nodes using BFS.

        Args:
            source_id: Starting node ID
            target_id: Destination node ID

        Returns:
            List of node dicts along the path, or None if no path exists
        """
        if source_id == target_id:
            node = self.graph_store.get_node(source_id)
            return [node.to_dict()] if node else None

        # Build adjacency list from all edges
        adjacency: dict[str, set[str]] = defaultdict(set)
        with self.graph_store._transaction() as cursor:
            cursor.execute("SELECT source_id, target_id FROM edges")
            for row in cursor.fetchall():
                adjacency[row[0]].add(row[1])
                adjacency[row[1]].add(row[0])

        # BFS
        visited: set[str] = {source_id}
        queue: deque[list[str]] = deque([[source_id]])

        while queue:
            path = queue.popleft()
            current = path[-1]

            for neighbor in adjacency.get(current, set()):
                if neighbor == target_id:
                    full_path = path + [neighbor]
                    result = []
                    for nid in full_path:
                        node = self.graph_store.get_node(nid)
                        if node:
                            result.append(node.to_dict())
                    return result

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return None

    def get_connected_components(self) -> list[list[str]]:
        """Find clusters of connected nodes in the graph.

        Returns:
            List of components, each a list of node IDs
        """
        # Build undirected adjacency
        adjacency: dict[str, set[str]] = defaultdict(set)
        all_node_ids: set[str] = set()

        with self.graph_store._transaction() as cursor:
            cursor.execute("SELECT id FROM nodes")
            for row in cursor.fetchall():
                all_node_ids.add(row[0])

            cursor.execute("SELECT source_id, target_id FROM edges")
            for row in cursor.fetchall():
                adjacency[row[0]].add(row[1])
                adjacency[row[1]].add(row[0])

        visited: set[str] = set()
        components: list[list[str]] = []

        for node_id in all_node_ids:
            if node_id in visited:
                continue

            component: list[str] = []
            stack: list[str] = [node_id]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)

                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        stack.append(neighbor)

            components.append(sorted(component))

        # Sort components by size descending
        components.sort(key=len, reverse=True)
        return components

    def aggregate_by_type(self) -> dict[str, dict[str, Any]]:
        """Get aggregation statistics per node type.

        Returns:
            Dict mapping node type to aggregated stats
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT
                    node_type,
                    COUNT(*) as count,
                    AVG(importance_score) as avg_importance,
                    MIN(importance_score) as min_importance,
                    MAX(importance_score) as max_importance,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM nodes
                GROUP BY node_type
                ORDER BY count DESC
            """)

            result: dict[str, dict[str, Any]] = {}
            for row in cursor.fetchall():
                result[row[0]] = {
                    "count": row[1],
                    "avg_importance": round(row[2], 3) if row[2] else 0.0,
                    "min_importance": row[3],
                    "max_importance": row[4],
                    "oldest": row[5],
                    "newest": row[6],
                }

            return result

    def get_most_connected_nodes(self, limit: int = 10) -> list[dict]:
        """Get nodes with the most edges (highest degree).

        Args:
            limit: Maximum number of nodes to return

        Returns:
            List of node dicts with edge count
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT n.*, COUNT(DISTINCT e.id) as edge_count
                FROM nodes n
                LEFT JOIN edges e ON e.source_id = n.id OR e.target_id = n.id
                GROUP BY n.id
                ORDER BY edge_count DESC
                LIMIT ?
                """,
                (limit,),
            )

            results = []
            for row in cursor.fetchall():
                node = self.graph_store._row_to_node(row)
                node_dict = node.to_dict()
                node_dict["edge_count"] = row["edge_count"]
                results.append(node_dict)

            return results

    def search_by_importance(
        self,
        min_score: float,
        max_score: float = 1.0,
    ) -> list[dict]:
        """Filter nodes by importance score range.

        Args:
            min_score: Minimum importance score (inclusive)
            max_score: Maximum importance score (inclusive)

        Returns:
            List of matching nodes as dicts
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT * FROM nodes
                WHERE importance_score >= ? AND importance_score <= ?
                ORDER BY importance_score DESC, created_at DESC
                """,
                (min_score, max_score),
            )
            return [self.graph_store._row_to_node(row).to_dict() for row in cursor.fetchall()]
