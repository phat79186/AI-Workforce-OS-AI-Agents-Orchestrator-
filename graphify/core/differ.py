"""
Graph differ.

Compares two snapshots of a project graph and produces
a structured diff of added, removed, and modified nodes and edges.

Useful for tracking what changed between scans and for impact analysis.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GraphDiff:
    """Result of comparing two graph snapshots."""

    project_id: str = ""
    before_label: str = ""
    after_label: str = ""
    nodes_added: list[dict] = field(default_factory=list)
    nodes_removed: list[dict] = field(default_factory=list)
    nodes_modified: list[dict] = field(default_factory=list)
    edges_added: list[dict] = field(default_factory=list)
    edges_removed: list[dict] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """True if any changes were detected."""
        return bool(
            self.nodes_added
            or self.nodes_removed
            or self.nodes_modified
            or self.edges_added
            or self.edges_removed
        )

    @property
    def summary(self) -> dict:
        """Compact summary counts."""
        return {
            "nodes_added": len(self.nodes_added),
            "nodes_removed": len(self.nodes_removed),
            "nodes_modified": len(self.nodes_modified),
            "edges_added": len(self.edges_added),
            "edges_removed": len(self.edges_removed),
            "has_changes": self.has_changes,
        }

    def to_dict(self) -> dict:
        """Full serializable representation."""
        return {
            "project_id": self.project_id,
            "before": self.before_label,
            "after": self.after_label,
            "summary": self.summary,
            "nodes_added": self.nodes_added,
            "nodes_removed": self.nodes_removed,
            "nodes_modified": self.nodes_modified,
            "edges_added": self.edges_added,
            "edges_removed": self.edges_removed,
        }


class GraphDiffer:
    """Compare two snapshots of a project graph."""

    def __init__(self, get_conn_fn: Callable[[], sqlite3.Connection]) -> None:
        self._get_conn = get_conn_fn

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    def take_snapshot(self, project_id: str, label: str = "") -> int:
        """Capture current graph state.  Returns snapshot ID."""
        conn = self._get_conn()
        node_rows = conn.execute(
            "SELECT id FROM nodes WHERE project_id = ?", (project_id,)
        ).fetchall()
        edge_rows = conn.execute(
            "SELECT source_id || '→' || target_id || ':' || edge_type AS eid "
            "FROM edges WHERE project_id = ?",
            (project_id,),
        ).fetchall()

        node_ids = sorted(r["id"] for r in node_rows)
        edge_ids = sorted(r["eid"] for r in edge_rows)

        cur = conn.execute(
            """INSERT INTO graph_snapshots
               (project_id, created_at, node_count, edge_count, node_ids, edge_ids, label)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                time.time(),
                len(node_ids),
                len(edge_ids),
                json.dumps(node_ids),
                json.dumps(edge_ids),
                label,
            ),
        )
        conn.commit()
        snap_id = cur.lastrowid or 0
        logger.info("Snapshot #%d: %d nodes, %d edges", snap_id, len(node_ids), len(edge_ids))
        return snap_id

    def list_snapshots(self, project_id: str, limit: int = 20) -> list[dict]:
        """List recent snapshots for a project."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, created_at, node_count, edge_count, label
               FROM graph_snapshots
               WHERE project_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (project_id, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "node_count": r["node_count"],
                "edge_count": r["edge_count"],
                "label": r["label"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Diffing
    # ------------------------------------------------------------------

    def diff_snapshots(self, snap_a_id: int, snap_b_id: int) -> GraphDiff:
        """Compare two snapshots by ID."""
        conn = self._get_conn()
        a = conn.execute("SELECT * FROM graph_snapshots WHERE id = ?", (snap_a_id,)).fetchone()
        b = conn.execute("SELECT * FROM graph_snapshots WHERE id = ?", (snap_b_id,)).fetchone()
        if not a or not b:
            return GraphDiff()

        a_nodes = set(json.loads(a["node_ids"]))
        b_nodes = set(json.loads(b["node_ids"]))
        a_edges = set(json.loads(a["edge_ids"]))
        b_edges = set(json.loads(b["edge_ids"]))

        diff = GraphDiff(
            project_id=a["project_id"],
            before_label=a["label"],
            after_label=b["label"],
        )

        # Nodes
        added_ids = b_nodes - a_nodes
        removed_ids = a_nodes - b_nodes

        for nid in added_ids:
            row = conn.execute(
                "SELECT id, name, node_type, file_path FROM nodes WHERE id = ?", (nid,)
            ).fetchone()
            if row:
                diff.nodes_added.append(dict(row))

        for nid in removed_ids:
            diff.nodes_removed.append({"id": nid})

        # Edges
        for eid in b_edges - a_edges:
            diff.edges_added.append({"edge": eid})
        for eid in a_edges - b_edges:
            diff.edges_removed.append({"edge": eid})

        return diff

    def diff_current(self, project_id: str, snapshot_id: int) -> GraphDiff:
        """Compare a snapshot against the current graph state."""
        current_snap = self.take_snapshot(project_id, label="_current_temp")
        result = self.diff_snapshots(snapshot_id, current_snap)
        # Clean up temp snapshot
        conn = self._get_conn()
        conn.execute("DELETE FROM graph_snapshots WHERE id = ?", (current_snap,))
        conn.commit()
        return result
