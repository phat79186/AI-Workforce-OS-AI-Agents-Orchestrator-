"""
Graph Store - SQLite-backed graph database for the agentic team context system.

Independent implementation — does NOT import from orchestrator/context.
Provides node/edge CRUD, FTS5 full-text search, and transaction support.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from agentic_team.context.models.schemas import Edge, EdgeType, Node, NodeType


class GraphStore:
    """SQLite-backed graph database for agentic team context storage."""

    def __init__(self, db_path: str | None = None):
        """Initialize the graph store.

        Args:
            db_path: Path to SQLite database file.
                     Defaults to ~/.agentic-team/context.db
                     Override with AGENTIC_TEAM_CONTEXT_DB env var.
        """
        self.logger = logging.getLogger("agentic_team.context.graph_store")

        if db_path is None:
            db_path = os.environ.get("AGENTIC_TEAM_CONTEXT_DB")

        if db_path is None:
            default_dir = Path.home() / ".agentic-team"
            default_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(default_dir / "context.db")

        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database transactions."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        with self._transaction() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    metadata TEXT DEFAULT '{}',
                    tags TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    importance_score REAL DEFAULT 1.0,
                    extra_data TEXT DEFAULT '{}'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    node_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model_name TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_nodes_importance ON nodes(importance_score)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type)")

            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                    id, title, content, tags,
                    content='nodes',
                    content_rowid='rowid'
                )
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                    INSERT INTO nodes_fts(id, title, content, tags)
                    VALUES (new.id, new.title, new.content, new.tags);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                    INSERT INTO nodes_fts(nodes_fts, id, title, content, tags)
                    VALUES ('delete', old.id, old.title, old.content, old.tags);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                    INSERT INTO nodes_fts(nodes_fts, id, title, content, tags)
                    VALUES ('delete', old.id, old.title, old.content, old.tags);
                    INSERT INTO nodes_fts(id, title, content, tags)
                    VALUES (new.id, new.title, new.content, new.tags);
                END
            """)

            # Migrate: add project_id column if missing (backward-compatible)
            try:
                cursor.execute("ALTER TABLE nodes ADD COLUMN project_id TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # Column already exists
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project_id)")

        self.logger.info("Agentic team graph store initialized at %s", self.db_path)

    def add_node(self, node: Node) -> str:
        """Add a node to the graph.

        Args:
            node: Node to add.

        Returns:
            Node ID.
        """
        node_dict = node.to_dict()
        extra_keys = set(node_dict.keys()) - {
            "id",
            "node_type",
            "title",
            "content",
            "metadata",
            "tags",
            "created_at",
            "updated_at",
            "importance_score",
            "embedding",
        }
        extra_data = {k: node_dict[k] for k in extra_keys}

        with self._transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO nodes
                (id, node_type, title, content, metadata, tags,
                 created_at, updated_at, importance_score, extra_data, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    node_type = excluded.node_type,
                    title = excluded.title,
                    content = excluded.content,
                    metadata = excluded.metadata,
                    tags = excluded.tags,
                    updated_at = excluded.updated_at,
                    importance_score = excluded.importance_score,
                    extra_data = excluded.extra_data,
                    project_id = excluded.project_id
                """,
                (
                    node.id,
                    node.node_type.value,
                    node.title,
                    node.content,
                    json.dumps(node.metadata),
                    json.dumps(node.tags),
                    node.created_at.isoformat(),
                    node.updated_at.isoformat(),
                    node.importance_score,
                    json.dumps(extra_data),
                    node.project_id,
                ),
            )

        self.logger.debug("Added node %s (%s)", node.id, node.node_type.value)
        return node.id

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID.

        Args:
            node_id: Node ID.

        Returns:
            Node or None if not found.
        """
        with self._transaction() as cursor:
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_node(row)

    def _row_to_node(self, row: sqlite3.Row) -> Node:
        """Convert database row to Node object."""
        data: dict[str, Any] = {
            "id": row["id"],
            "node_type": row["node_type"],
            "title": row["title"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]),
            "tags": json.loads(row["tags"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "importance_score": row["importance_score"],
            "project_id": row["project_id"] if "project_id" in row.keys() else "",
        }
        extra_data = json.loads(row["extra_data"]) if row["extra_data"] else {}
        data.update(extra_data)
        return Node.from_dict(data)

    def update_node(self, node: Node) -> bool:
        """Update an existing node.

        Args:
            node: Node with updated data.

        Returns:
            True if updated, False if not found.
        """
        node.updated_at = datetime.now(timezone.utc)
        node_dict = node.to_dict()
        extra_keys = set(node_dict.keys()) - {
            "id",
            "node_type",
            "title",
            "content",
            "metadata",
            "tags",
            "created_at",
            "updated_at",
            "importance_score",
            "embedding",
        }
        extra_data = {k: node_dict[k] for k in extra_keys}

        with self._transaction() as cursor:
            cursor.execute(
                """
                UPDATE nodes SET
                    node_type = ?,
                    title = ?,
                    content = ?,
                    metadata = ?,
                    tags = ?,
                    updated_at = ?,
                    importance_score = ?,
                    extra_data = ?,
                    project_id = ?
                WHERE id = ?
                """,
                (
                    node.node_type.value,
                    node.title,
                    node.content,
                    json.dumps(node.metadata),
                    json.dumps(node.tags),
                    node.updated_at.isoformat(),
                    node.importance_score,
                    json.dumps(extra_data),
                    node.project_id,
                    node.id,
                ),
            )
            return cursor.rowcount > 0

    def delete_nodes_by_project(self, project_id: str) -> int:
        """Delete all nodes (and cascading edges) for a project in a single transaction.

        Args:
            project_id: The project identifier.

        Returns:
            Number of nodes deleted.
        """
        with self._transaction() as cursor:
            cursor.execute(
                "DELETE FROM edges WHERE source_id IN (SELECT id FROM nodes WHERE project_id = ?) "
                "OR target_id IN (SELECT id FROM nodes WHERE project_id = ?)",
                (project_id, project_id),
            )
            cursor.execute("DELETE FROM nodes WHERE project_id = ?", (project_id,))
            return cursor.rowcount

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its associated edges.

        Args:
            node_id: Node ID.

        Returns:
            True if deleted, False if not found.
        """
        with self._transaction() as cursor:
            cursor.execute(
                "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
                (node_id, node_id),
            )
            cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            return cursor.rowcount > 0

    def add_edge(self, edge: Edge) -> str:
        """Add an edge between nodes.

        Args:
            edge: Edge to add.

        Returns:
            Edge ID.
        """
        with self._transaction() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO edges
                (id, source_id, target_id, edge_type, weight, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type.value,
                    edge.weight,
                    json.dumps(edge.metadata),
                    edge.created_at.isoformat(),
                ),
            )

        self.logger.debug(
            "Added edge %s --[%s]--> %s",
            edge.source_id,
            edge.edge_type.value,
            edge.target_id,
        )
        return edge.id

    def get_edge(self, edge_id: str) -> Edge | None:
        """Get an edge by ID."""
        with self._transaction() as cursor:
            cursor.execute("SELECT * FROM edges WHERE id = ?", (edge_id,))
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_edge(row)

    def _row_to_edge(self, row: sqlite3.Row) -> Edge:
        """Convert database row to Edge object."""
        return Edge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            edge_type=EdgeType(row["edge_type"]),
            weight=row["weight"],
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        with self._transaction() as cursor:
            cursor.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
            return cursor.rowcount > 0

    def get_edges_from(self, node_id: str, edge_type: EdgeType | None = None) -> list[Edge]:
        """Get all outgoing edges from a node."""
        with self._transaction() as cursor:
            if edge_type:
                cursor.execute(
                    "SELECT * FROM edges WHERE source_id = ? AND edge_type = ?",
                    (node_id, edge_type.value),
                )
            else:
                cursor.execute("SELECT * FROM edges WHERE source_id = ?", (node_id,))
            return [self._row_to_edge(row) for row in cursor.fetchall()]

    def get_edges_to(self, node_id: str, edge_type: EdgeType | None = None) -> list[Edge]:
        """Get all incoming edges to a node."""
        with self._transaction() as cursor:
            if edge_type:
                cursor.execute(
                    "SELECT * FROM edges WHERE target_id = ? AND edge_type = ?",
                    (node_id, edge_type.value),
                )
            else:
                cursor.execute("SELECT * FROM edges WHERE target_id = ?", (node_id,))
            return [self._row_to_edge(row) for row in cursor.fetchall()]

    def query_nodes(
        self,
        node_type: NodeType | None = None,
        tags: list[str] | None = None,
        min_importance: float | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        project_id: str | None = None,
    ) -> list[Node]:
        """Query nodes with filters.

        Args:
            node_type: Filter by node type.
            tags: Filter by tags (any match).
            min_importance: Minimum importance score.
            created_after: Created after this time.
            created_before: Created before this time.
            limit: Maximum results.
            offset: Skip first N results.
            project_id: Filter by project ID.

        Returns:
            List of matching nodes.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if node_type:
            conditions.append("node_type = ?")
            params.append(node_type.value)

        if min_importance is not None:
            conditions.append("importance_score >= ?")
            params.append(min_importance)

        if created_after:
            conditions.append("created_at >= ?")
            params.append(created_after.isoformat())

        if created_before:
            conditions.append("created_at <= ?")
            params.append(created_before.isoformat())

        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM nodes
            WHERE {where_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ? OFFSET ?
        """  # noqa: S608
        params.extend([limit, offset])

        with self._transaction() as cursor:
            cursor.execute(query, params)
            nodes = [self._row_to_node(row) for row in cursor.fetchall()]

        if tags:
            nodes = [n for n in nodes if any(t in n.tags for t in tags)]

        return nodes

    def full_text_search(self, query: str, limit: int = 50) -> list[tuple[Node, float]]:
        """Perform FTS5 full-text search on nodes.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of (node, relevance_score) tuples.
        """
        with self._transaction() as cursor:
            cursor.execute(
                """
                SELECT nodes.*, bm25(nodes_fts) as score
                FROM nodes_fts
                JOIN nodes ON nodes_fts.id = nodes.id
                WHERE nodes_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (query, limit),
            )

            results = []
            for row in cursor.fetchall():
                node = self._row_to_node(row)
                score = abs(row["score"])
                results.append((node, score))

        return results

    def node_count(self) -> int:
        """Return total number of nodes."""
        with self._transaction() as cursor:
            cursor.execute("SELECT COUNT(*) FROM nodes")
            return cursor.fetchone()[0]

    def edge_count(self) -> int:
        """Return total number of edges."""
        with self._transaction() as cursor:
            cursor.execute("SELECT COUNT(*) FROM edges")
            return cursor.fetchone()[0]

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        with self._transaction() as cursor:
            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM edges")
            total_edges = cursor.fetchone()[0]

            cursor.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type")
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type")
            edge_type_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": type_counts,
            "edges_by_type": edge_type_counts,
        }

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
