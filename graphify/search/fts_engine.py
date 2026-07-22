"""
FTS5 full-text search engine for the graphify graph.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

from graphify.core.graph import GraphStore
from graphify.core.schema import Node, NodeType

logger = logging.getLogger(__name__)

# Characters that could break FTS5 queries
_FTS_UNSAFE_RE = re.compile(r"[^\w\s]", re.UNICODE)


class FTSEngine:
    """Full-text search over graph nodes using SQLite FTS5."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def search(
        self,
        query: str,
        project_id: str = "",
        node_type: NodeType | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search nodes using FTS5 with BM25 ranking.

        Returns list of dicts with ``node``, ``score``, and ``snippet``.
        """
        sanitized = self._sanitize_query(query)
        if not sanitized.strip():
            return []

        conn = self._store._get_conn()  # noqa: SLF001

        # Build FTS match with optional project/type filter
        params: list[Any] = [sanitized]
        type_clause = ""
        project_clause = ""

        if project_id:
            project_clause = "AND n.project_id = ?"
            params.append(project_id)
        if node_type is not None:
            type_clause = "AND n.node_type = ?"
            params.append(node_type.value)

        params.append(min(limit, 500))

        sql = f"""
            SELECT n.*, bm25(nodes_fts) AS score,
                   snippet(nodes_fts, 3, '<b>', '</b>', '...', 40) AS snippet
            FROM nodes_fts fts
            JOIN nodes n ON n.id = fts.id
            WHERE nodes_fts MATCH ?
            {project_clause}
            {type_clause}
            ORDER BY score
            LIMIT ?
        """

        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            logger.warning("FTS query failed for: %s", query)
            return []

        results = []
        for row in rows:
            results.append(
                {
                    "node": GraphStore._row_to_node(row),  # noqa: SLF001
                    "score": abs(row["score"]),
                    "snippet": row["snippet"],
                }
            )
        return results

    def search_by_name(
        self,
        name: str,
        project_id: str = "",
        limit: int = 20,
    ) -> list[Node]:
        """Exact-prefix name search (faster than FTS for symbol lookup)."""
        conn = self._store._get_conn()  # noqa: SLF001
        params: list[Any] = [f"{name}%"]
        project_clause = ""
        if project_id:
            project_clause = "AND project_id = ?"
            params.append(project_id)
        params.append(min(limit, 500))

        rows = conn.execute(
            f"SELECT * FROM nodes WHERE name LIKE ? {project_clause} LIMIT ?",
            params,
        ).fetchall()
        return [GraphStore._row_to_node(r) for r in rows]  # noqa: SLF001

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Remove characters that could break FTS5 MATCH syntax."""
        cleaned = _FTS_UNSAFE_RE.sub(" ", query)
        tokens = cleaned.split()
        if not tokens:
            return ""
        # Wrap multi-word in quotes for phrase search
        if len(tokens) > 1:
            return " ".join(tokens)
        return tokens[0]
