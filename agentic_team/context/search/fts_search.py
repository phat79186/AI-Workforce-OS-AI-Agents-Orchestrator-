"""
FTS5 Search — Lightweight full-text search for Agentic Team Context.

Independent implementation — does NOT import from orchestrator/context.
Uses the FTS5 virtual table already maintained by GraphStore to provide
full-text search, ranking, and prefix-based autocomplete.
"""

from __future__ import annotations

import logging
from typing import Any

from agentic_team.context.models.schemas import Node, NodeType
from agentic_team.context.store.graph_store import GraphStore


class FTSSearch:
    """SQLite FTS5-backed search over the agentic team context graph."""

    def __init__(self, graph_store: GraphStore):
        """Initialize FTS search.

        Args:
            graph_store: Graph store instance whose ``nodes_fts`` table
                         is kept in sync via triggers.
        """
        self.logger = logging.getLogger("agentic_team.context.fts_search")
        self.graph_store = graph_store

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Wrap each token in double-quotes for safe FTS5 MATCH syntax.

        Args:
            query: Raw query string.

        Returns:
            Sanitized FTS5-compatible query, or empty string.
        """
        words = query.split()
        if not words:
            return ""
        return " ".join(f'"{w}"' for w in words if w.strip())

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 10,
        node_types: list[NodeType] | None = None,
    ) -> list[tuple[Node, float]]:
        """Full-text search using FTS5 MATCH.

        Args:
            query: Search query.
            limit: Maximum number of results.
            node_types: Optional filter by node type(s).

        Returns:
            List of ``(Node, score)`` tuples ordered by relevance.
        """
        safe_query = self._sanitize_query(query)
        if not safe_query:
            return []

        try:
            with self.graph_store._transaction() as cursor:
                cursor.execute(
                    """
                    SELECT nodes.*, bm25(nodes_fts) AS score
                    FROM nodes_fts
                    JOIN nodes ON nodes_fts.id = nodes.id
                    WHERE nodes_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (safe_query, limit * 2),
                )
                rows = cursor.fetchall()
        except Exception as exc:
            self.logger.debug("FTS search failed for query '%s': %s", query, exc)
            return []

        results: list[tuple[Node, float]] = []
        for row in rows:
            node = self.graph_store._row_to_node(row)
            if node_types and node.node_type not in node_types:
                continue
            score = abs(row["score"])
            results.append((node, score))
            if len(results) >= limit:
                break

        return results

    def search_with_ranking(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[Node, float]]:
        """Search using FTS5 rank function for relevance ordering.

        This is a convenience wrapper that returns results ranked by the
        built-in ``rank`` column provided by FTS5.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of ``(Node, score)`` tuples.
        """
        safe_query = self._sanitize_query(query)
        if not safe_query:
            return []

        try:
            with self.graph_store._transaction() as cursor:
                cursor.execute(
                    """
                    SELECT nodes.*, rank AS score
                    FROM nodes_fts
                    JOIN nodes ON nodes_fts.id = nodes.id
                    WHERE nodes_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (safe_query, limit),
                )
                rows = cursor.fetchall()
        except Exception as exc:
            self.logger.debug("FTS ranked search failed for query '%s': %s", query, exc)
            return []

        results: list[tuple[Node, float]] = []
        for row in rows:
            node = self.graph_store._row_to_node(row)
            results.append((node, abs(row["score"])))

        return results

    def suggest_completions(
        self,
        prefix: str,
        limit: int = 5,
    ) -> list[str]:
        """Suggest title completions based on an FTS5 prefix search.

        Args:
            prefix: Partial text to match against node titles.
            limit: Maximum suggestions to return.

        Returns:
            List of matching node titles.
        """
        if not prefix or not prefix.strip():
            return []

        fts_prefix = f'"{prefix}"*'

        try:
            with self.graph_store._transaction() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT nodes.title
                    FROM nodes_fts
                    JOIN nodes ON nodes_fts.id = nodes.id
                    WHERE nodes_fts MATCH ?
                    ORDER BY bm25(nodes_fts)
                    LIMIT ?
                    """,
                    (fts_prefix, limit),
                )
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as exc:
            self.logger.debug("FTS suggest failed for prefix '%s': %s", prefix, exc)
            return []

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return basic statistics about the FTS index."""
        try:
            with self.graph_store._transaction() as cursor:
                cursor.execute("SELECT COUNT(*) FROM nodes_fts")
                total = cursor.fetchone()[0]
            return {"fts_indexed_rows": total}
        except Exception:
            return {"fts_indexed_rows": 0}
