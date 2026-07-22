"""
SQLite-backed graph store with FTS5 full-text search.

Handles node/edge persistence, full-text indexing, bulk operations,
project isolation, and safe concurrent access via WAL mode.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Generator

from graphify.core.exceptions import GraphError
from graphify.core.schema import Edge, EdgeType, Node, NodeType, ProjectSummary

logger = logging.getLogger(__name__)


class GraphStore:
    """Persistent graph backed by SQLite with FTS5."""

    SCHEMA_VERSION = 3

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._all_conns: list[sqlite3.Connection] = []
        self._conn_lock = threading.Lock()
        self._closed = False
        self._init_schema()
        self._run_migrations()
        logger.info("GraphStore initialised: %s", db_path)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> GraphStore:
        """Enter the context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager and close connections."""
        self.close()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """Thread-local connection with WAL mode."""
        if self._closed:
            raise GraphError("GraphStore is closed")
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
            with self._conn_lock:
                self._all_conns.append(conn)
        return conn

    def get_connection_factory(self) -> Callable[[], sqlite3.Connection]:
        """Return a callable that produces thread-local connections."""
        return self._get_conn

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for atomic transactions."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """Create tables, indices, and FTS virtual table."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id            TEXT PRIMARY KEY,
                node_type     TEXT NOT NULL,
                name          TEXT NOT NULL DEFAULT '',
                qualified_name TEXT NOT NULL DEFAULT '',
                file_path     TEXT NOT NULL DEFAULT '',
                language      TEXT NOT NULL DEFAULT '',
                line_start    INTEGER NOT NULL DEFAULT 0,
                line_end      INTEGER NOT NULL DEFAULT 0,
                content       TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                project_id    TEXT NOT NULL DEFAULT '',
                created_at    REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS edges (
                source_id    TEXT NOT NULL,
                target_id    TEXT NOT NULL,
                edge_type    TEXT NOT NULL,
                weight       REAL NOT NULL DEFAULT 1.0,
                confidence   REAL NOT NULL DEFAULT 1.0,
                provenance   TEXT NOT NULL DEFAULT 'EXTRACTED',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                project_id   TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source_id, target_id, edge_type)
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_project
                ON nodes(project_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type
                ON nodes(node_type, project_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_file
                ON nodes(file_path, project_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_name
                ON nodes(name, project_id);
            CREATE INDEX IF NOT EXISTS idx_edges_source
                ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target
                ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_project
                ON edges(project_id);

            CREATE TABLE IF NOT EXISTS project_meta (
                project_id   TEXT PRIMARY KEY,
                root_path    TEXT NOT NULL,
                name         TEXT NOT NULL DEFAULT '',
                summary_json TEXT NOT NULL DEFAULT '{}',
                scanned_at   REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );
        """)

        # FTS5 virtual table (CREATE IF NOT EXISTS not supported for FTS5)
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE nodes_fts USING fts5(
                    id, name, qualified_name, content,
                    content=nodes,
                    content_rowid=rowid,
                    tokenize='porter unicode61'
                )
            """)
        except sqlite3.OperationalError:
            pass  # already exists

        # Triggers to keep FTS in sync
        for trigger_sql in [
            """CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                INSERT INTO nodes_fts(rowid, id, name, qualified_name, content)
                VALUES (new.rowid, new.id, new.name, new.qualified_name, new.content);
            END""",
            """CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, id, name, qualified_name, content)
                VALUES ('delete', old.rowid, old.id, old.name, old.qualified_name, old.content);
            END""",
            """CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, id, name, qualified_name, content)
                VALUES ('delete', old.rowid, old.id, old.name, old.qualified_name, old.content);
                INSERT INTO nodes_fts(rowid, id, name, qualified_name, content)
                VALUES (new.rowid, new.id, new.name, new.qualified_name, new.content);
            END""",
        ]:
            try:
                conn.execute(trigger_sql)
            except sqlite3.OperationalError:
                pass
        conn.commit()

    def _run_migrations(self) -> None:
        """Apply any pending schema migrations."""
        from graphify.core.migrations import migrate  # noqa: C0415

        conn = self._get_conn()
        migrate(conn, target=self.SCHEMA_VERSION)

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        """Insert or update a node."""
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO nodes
                   (id, node_type, name, qualified_name, file_path, language,
                    line_start, line_end, content, metadata_json, project_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       node_type=excluded.node_type, name=excluded.name,
                       qualified_name=excluded.qualified_name, file_path=excluded.file_path,
                       language=excluded.language, line_start=excluded.line_start,
                       line_end=excluded.line_end, content=excluded.content,
                       metadata_json=excluded.metadata_json""",
                (
                    node.id,
                    node.node_type.value,
                    node.name,
                    node.qualified_name,
                    node.file_path,
                    node.language,
                    node.line_start,
                    node.line_end,
                    node.content,
                    json.dumps(node.metadata),
                    node.project_id,
                    node.created_at,
                ),
            )

    def add_nodes_bulk(self, nodes: list[Node]) -> int:
        """Bulk insert/upsert nodes. Returns count inserted."""
        if not nodes:
            return 0
        with self._transaction() as conn:
            conn.executemany(
                """INSERT INTO nodes
                   (id, node_type, name, qualified_name, file_path, language,
                    line_start, line_end, content, metadata_json, project_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       node_type=excluded.node_type, name=excluded.name,
                       qualified_name=excluded.qualified_name, file_path=excluded.file_path,
                       language=excluded.language, line_start=excluded.line_start,
                       line_end=excluded.line_end, content=excluded.content,
                       metadata_json=excluded.metadata_json""",
                [
                    (
                        n.id,
                        n.node_type.value,
                        n.name,
                        n.qualified_name,
                        n.file_path,
                        n.language,
                        n.line_start,
                        n.line_end,
                        n.content,
                        json.dumps(n.metadata),
                        n.project_id,
                        n.created_at,
                    )
                    for n in nodes
                ],
            )
        logger.debug("Bulk inserted %d nodes", len(nodes))
        return len(nodes)

    def get_node(self, node_id: str) -> Node | None:
        """Retrieve a single node by ID."""
        row = self._get_conn().execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_node(row) if row else None

    def get_nodes(
        self,
        project_id: str = "",
        node_type: NodeType | None = None,
        file_path: str | None = None,
        limit: int = 1000,
    ) -> list[Node]:
        """Query nodes with optional filters."""
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]

        if node_type is not None:
            clauses.append("node_type = ?")
            params.append(node_type.value)
        if file_path is not None:
            clauses.append("file_path = ?")
            params.append(file_path)

        params.append(min(limit, 10_000))
        sql = f"SELECT * FROM nodes WHERE {' AND '.join(clauses)} LIMIT ?"
        rows = self._get_conn().execute(sql, params).fetchall()
        return [self._row_to_node(r) for r in rows]

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its connected edges."""
        with self._transaction() as conn:
            conn.execute(
                "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
                (node_id, node_id),
            )
            cursor = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def add_edge(self, edge: Edge) -> None:
        """Insert or update an edge."""
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO edges
                   (source_id, target_id, edge_type, weight, confidence,
                    provenance, metadata_json, project_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET
                       weight=excluded.weight, confidence=excluded.confidence,
                       provenance=excluded.provenance,
                       metadata_json=excluded.metadata_json""",
                (
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type.value,
                    edge.weight,
                    edge.confidence,
                    edge.provenance,
                    json.dumps(edge.metadata),
                    edge.project_id,
                ),
            )

    def add_edges_bulk(self, edges: list[Edge]) -> int:
        """Bulk insert/upsert edges. Returns count inserted."""
        if not edges:
            return 0
        with self._transaction() as conn:
            conn.executemany(
                """INSERT INTO edges
                   (source_id, target_id, edge_type, weight, confidence,
                    provenance, metadata_json, project_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET
                       weight=excluded.weight, confidence=excluded.confidence,
                       provenance=excluded.provenance,
                       metadata_json=excluded.metadata_json""",
                [
                    (
                        e.source_id,
                        e.target_id,
                        e.edge_type.value,
                        e.weight,
                        e.confidence,
                        e.provenance,
                        json.dumps(e.metadata),
                        e.project_id,
                    )
                    for e in edges
                ],
            )
        logger.debug("Bulk inserted %d edges", len(edges))
        return len(edges)

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: EdgeType | None = None,
        project_id: str = "",
    ) -> list[Edge]:
        """Query edges with optional filters."""
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]

        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(source_id)
        if target_id is not None:
            clauses.append("target_id = ?")
            params.append(target_id)
        if edge_type is not None:
            clauses.append("edge_type = ?")
            params.append(edge_type.value)

        sql = f"SELECT * FROM edges WHERE {' AND '.join(clauses)}"
        rows = self._get_conn().execute(sql, params).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "outgoing",
        edge_type: EdgeType | None = None,
    ) -> list[tuple[Node, Edge]]:
        """Get neighboring nodes with their connecting edges."""
        if direction == "outgoing":
            col, join_col = "source_id", "target_id"
        elif direction == "incoming":
            col, join_col = "target_id", "source_id"
        else:
            raise ValueError(f"direction must be 'outgoing' or 'incoming', got '{direction}'")

        params: list[Any] = [node_id]
        type_clause = ""
        if edge_type is not None:
            type_clause = "AND e.edge_type = ?"
            params.append(edge_type.value)

        sql = f"""
            SELECT n.*, e.source_id AS e_source, e.target_id AS e_target,
                   e.edge_type AS e_type, e.weight AS e_weight,
                   e.confidence AS e_confidence, e.provenance AS e_provenance,
                   e.metadata_json AS e_meta, e.project_id AS e_project
            FROM edges e
            JOIN nodes n ON n.id = e.{join_col}
            WHERE e.{col} = ? {type_clause}
        """
        rows = self._get_conn().execute(sql, params).fetchall()

        results = []
        for r in rows:
            node = self._row_to_node(r)
            edge = Edge(
                source_id=r["e_source"],
                target_id=r["e_target"],
                edge_type=EdgeType(r["e_type"]),
                weight=r["e_weight"],
                confidence=r["e_confidence"],
                provenance=r["e_provenance"],
                metadata=json.loads(r["e_meta"]),
                project_id=r["e_project"],
            )
            results.append((node, edge))
        return results

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------

    def save_project_meta(self, summary: ProjectSummary) -> None:
        """Save or update project metadata."""
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO project_meta (project_id, root_path, name, summary_json, scanned_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(project_id) DO UPDATE SET
                       root_path=excluded.root_path, name=excluded.name,
                       summary_json=excluded.summary_json, scanned_at=excluded.scanned_at""",
                (
                    summary.project_id,
                    summary.root_path,
                    summary.name,
                    json.dumps(
                        {
                            "languages": summary.languages,
                            "total_files": summary.total_files,
                            "total_lines": summary.total_lines,
                            "total_classes": summary.total_classes,
                            "total_functions": summary.total_functions,
                            "total_tests": summary.total_tests,
                            "dependencies": summary.dependencies,
                            "frameworks": summary.frameworks,
                        }
                    ),
                    summary.scanned_at,
                ),
            )

    def get_project_meta(self, project_id: str) -> ProjectSummary | None:
        """Retrieve project metadata."""
        row = (
            self._get_conn()
            .execute("SELECT * FROM project_meta WHERE project_id = ?", (project_id,))
            .fetchone()
        )
        if not row:
            return None
        data = json.loads(row["summary_json"])
        return ProjectSummary(
            project_id=row["project_id"],
            root_path=row["root_path"],
            name=row["name"],
            languages=data.get("languages", {}),
            total_files=data.get("total_files", 0),
            total_lines=data.get("total_lines", 0),
            total_classes=data.get("total_classes", 0),
            total_functions=data.get("total_functions", 0),
            total_tests=data.get("total_tests", 0),
            dependencies=data.get("dependencies", []),
            frameworks=data.get("frameworks", []),
            scanned_at=row["scanned_at"],
        )

    def list_projects(self) -> list[ProjectSummary]:
        """List all scanned projects."""
        rows = (
            self._get_conn()
            .execute("SELECT * FROM project_meta ORDER BY scanned_at DESC")
            .fetchall()
        )
        result = []
        for r in rows:
            proj = self.get_project_meta(r["project_id"])
            if proj:
                result.append(proj)
        return result

    def delete_project(self, project_id: str) -> int:
        """Atomically delete all data for a project. Returns deleted node count."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM edges WHERE project_id = ?", (project_id,))
            cursor = conn.execute("DELETE FROM nodes WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM project_meta WHERE project_id = ?", (project_id,))
        count = cursor.rowcount
        logger.info("Deleted project %s: %d nodes removed", project_id, count)
        return count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self, project_id: str = "") -> dict[str, Any]:
        """Return graph statistics."""
        conn = self._get_conn()
        clause = "WHERE project_id = ?" if project_id else ""
        params = (project_id,) if project_id else ()

        node_count = conn.execute(f"SELECT COUNT(*) FROM nodes {clause}", params).fetchone()[0]
        edge_count = conn.execute(f"SELECT COUNT(*) FROM edges {clause}", params).fetchone()[0]

        type_counts = {}
        for row in conn.execute(
            f"SELECT node_type, COUNT(*) as cnt FROM nodes {clause} GROUP BY node_type", params
        ):
            type_counts[row["node_type"]] = row["cnt"]

        edge_type_counts = {}
        for row in conn.execute(
            f"SELECT edge_type, COUNT(*) as cnt FROM edges {clause} GROUP BY edge_type", params
        ):
            edge_type_counts[row["edge_type"]] = row["cnt"]

        return {
            "nodes": node_count,
            "edges": edge_count,
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "db_path": self._db_path,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Node:
        """Convert a DB row to a Node dataclass."""
        return Node(
            id=row["id"],
            node_type=NodeType(row["node_type"]),
            name=row["name"],
            qualified_name=row["qualified_name"],
            file_path=row["file_path"],
            language=row["language"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            content=row["content"],
            metadata=json.loads(row["metadata_json"]),
            project_id=row["project_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> Edge:
        """Convert a DB row to an Edge dataclass."""
        return Edge(
            source_id=row["source_id"],
            target_id=row["target_id"],
            edge_type=EdgeType(row["edge_type"]),
            weight=row["weight"],
            confidence=row["confidence"],
            provenance=row["provenance"],
            metadata=json.loads(row["metadata_json"]),
            project_id=row["project_id"],
        )

    def close(self) -> None:
        """Close all tracked connections across threads."""
        with self._conn_lock:
            for conn in self._all_conns:
                try:
                    conn.close()
                except Exception:  # pylint: disable=broad-except
                    pass
            self._all_conns.clear()
        self._local.conn = None
        self._closed = True

    # ------------------------------------------------------------------
    # Graph intelligence queries
    # ------------------------------------------------------------------

    def god_nodes(self, project_id: str = "", top_n: int = 20) -> list[dict[str, Any]]:
        """Return nodes with the highest total degree (in + out edges)."""
        conn = self._get_conn()
        sql = """
            SELECT node_id, SUM(cnt) AS degree FROM (
                SELECT source_id AS node_id, COUNT(*) AS cnt FROM edges
                WHERE project_id = ? GROUP BY source_id
                UNION ALL
                SELECT target_id AS node_id, COUNT(*) AS cnt FROM edges
                WHERE project_id = ? GROUP BY target_id
            ) GROUP BY node_id ORDER BY degree DESC LIMIT ?
        """
        rows = conn.execute(sql, (project_id, project_id, top_n)).fetchall()
        results = []
        for r in rows:
            node = self.get_node(r["node_id"])
            if node:
                results.append(
                    {
                        "node": node,
                        "degree": r["degree"],
                    }
                )
        return results

    def shortest_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 10,
    ) -> list[str] | None:
        """BFS shortest path between two nodes. Returns list of node IDs or None."""
        if start_id == end_id:
            return [start_id]

        conn = self._get_conn()
        visited = {start_id}
        parent: dict[str, str] = {}
        queue = [start_id]

        for _depth in range(max_depth):
            next_queue: list[str] = []
            if not queue:
                break
            placeholders = ",".join("?" for _ in queue)
            rows = conn.execute(
                f"""SELECT DISTINCT source_id, target_id FROM edges
                    WHERE source_id IN ({placeholders})
                    OR target_id IN ({placeholders})""",
                [*queue, *queue],
            ).fetchall()

            candidates = self._bfs_expand(rows, queue, visited)
            for node_id, from_id in candidates:
                visited.add(node_id)
                parent[node_id] = from_id
                if node_id == end_id:
                    return self._reconstruct_path(end_id, parent)
                next_queue.append(node_id)
            queue = next_queue
        return None

    @staticmethod
    def _bfs_expand(
        rows: list,
        queue: list[str],
        visited: set,
    ) -> list[tuple]:
        """Expand BFS frontier, returning (node_id, from_id) pairs."""
        results: list[tuple] = []
        queue_set = set(queue)
        for row in rows:
            for node_id, from_id in [
                (row["target_id"], row["source_id"]),
                (row["source_id"], row["target_id"]),
            ]:
                if from_id in queue_set and node_id not in visited:
                    results.append((node_id, from_id))
        return results

    @staticmethod
    def _reconstruct_path(end_id: str, parent: dict[str, str]) -> list[str]:
        """Trace back from end_id through parent map."""
        path = [end_id]
        current = end_id
        while current in parent:
            current = parent[current]
            path.append(current)
        path.reverse()
        return path

    def node_degree(self, node_id: str) -> dict[str, int]:
        """Return in-degree, out-degree, and total degree for a node."""
        conn = self._get_conn()
        out_deg = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE source_id = ?",
            (node_id,),
        ).fetchone()[0]
        in_deg = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE target_id = ?",
            (node_id,),
        ).fetchone()[0]
        return {"in_degree": in_deg, "out_degree": out_deg, "total": in_deg + out_deg}

    def delete_file_nodes(self, file_path: str, project_id: str) -> int:
        """Delete all nodes (and their edges) associated with a file path."""
        with self._transaction() as conn:
            node_ids = [
                r[0]
                for r in conn.execute(
                    "SELECT id FROM nodes WHERE file_path = ? AND project_id = ?",
                    (file_path, project_id),
                ).fetchall()
            ]
            if not node_ids:
                return 0
            placeholders = ",".join("?" for _ in node_ids)
            conn.execute(
                f"DELETE FROM edges WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
                [*node_ids, *node_ids],
            )
            cursor = conn.execute(
                f"DELETE FROM nodes WHERE id IN ({placeholders})",
                node_ids,
            )
        return cursor.rowcount
