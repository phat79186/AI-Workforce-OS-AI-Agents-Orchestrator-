"""Context Versioning - Track changes to nodes over time."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from orchestrator.context.store.graph_store import GraphStore


class ContextVersioning:
    """Version tracking for context graph nodes."""

    def __init__(self, graph_store: GraphStore):
        """Initialize versioning.

        Args:
            graph_store: Graph store instance
        """
        self.logger = logging.getLogger("context.versioning")
        self.graph_store = graph_store
        self._init_version_table()

    def _init_version_table(self) -> None:
        """Create the node_versions table if it doesn't exist."""
        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS node_versions (
                    id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    changed_at TEXT NOT NULL,
                    change_type TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_node ON node_versions(node_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_versions_node_ver "
                "ON node_versions(node_id, version)"
            )

    def record_version(self, node_id: str, change_type: str = "update") -> int:
        """Snapshot the current state of a node as a new version.

        Args:
            node_id: ID of the node to snapshot
            change_type: Type of change (e.g. "create", "update", "delete")

        Returns:
            The new version number
        """
        node = self.graph_store.get_node(node_id)
        if node is None:
            raise ValueError(f"Node {node_id} not found")

        with self.graph_store._transaction() as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(version), 0) FROM node_versions WHERE node_id = ?",
                (node_id,),
            )
            current_max = cursor.fetchone()[0]
            new_version = current_max + 1

            cursor.execute(
                """
                INSERT INTO node_versions
                    (id, node_id, version, content, metadata, changed_at, change_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    node_id,
                    new_version,
                    node.content,
                    json.dumps(node.metadata),
                    datetime.now(timezone.utc).isoformat(),
                    change_type,
                ),
            )

        self.logger.debug("Recorded version %s for node %s (%s)", new_version, node_id, change_type)
        return new_version

    def get_versions(self, node_id: str) -> list[dict[str, Any]]:
        """Get all versions of a node.

        Args:
            node_id: ID of the node

        Returns:
            List of version records ordered by version number
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT id, node_id, version, content, metadata, changed_at, change_type
                FROM node_versions
                WHERE node_id = ?
                ORDER BY version ASC
                """,
                (node_id,),
            )
            return [
                {
                    "id": row[0],
                    "node_id": row[1],
                    "version": row[2],
                    "content": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                    "changed_at": row[5],
                    "change_type": row[6],
                }
                for row in cursor.fetchall()
            ]

    def get_version(self, node_id: str, version: int) -> dict[str, Any] | None:
        """Get a specific version of a node.

        Args:
            node_id: ID of the node
            version: Version number to retrieve

        Returns:
            Version record or None if not found
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT id, node_id, version, content, metadata, changed_at, change_type
                FROM node_versions
                WHERE node_id = ? AND version = ?
                """,
                (node_id, version),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "node_id": row[1],
            "version": row[2],
            "content": row[3],
            "metadata": json.loads(row[4]) if row[4] else {},
            "changed_at": row[5],
            "change_type": row[6],
        }

    def rollback(self, node_id: str, version: int) -> bool:
        """Restore a node to a previous version.

        Args:
            node_id: ID of the node
            version: Version number to restore

        Returns:
            True if rollback succeeded, False otherwise
        """
        ver = self.get_version(node_id, version)
        if ver is None:
            self.logger.warning("Version %s not found for node %s", version, node_id)
            return False

        node = self.graph_store.get_node(node_id)
        if node is None:
            self.logger.warning("Node %s not found for rollback", node_id)
            return False

        # Record current state before rollback
        self.record_version(node_id, change_type="pre_rollback")

        node.content = ver["content"]
        node.metadata = ver["metadata"]
        self.graph_store.update_node(node)

        # Record the rollback itself
        self.record_version(node_id, change_type=f"rollback_to_v{version}")

        self.logger.info("Rolled back node %s to version %s", node_id, version)
        return True

    def get_change_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent changes across all nodes.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent version records, newest first
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT nv.id, nv.node_id, nv.version, nv.content, nv.metadata,
                       nv.changed_at, nv.change_type, n.title, n.node_type
                FROM node_versions nv
                LEFT JOIN nodes n ON nv.node_id = n.id
                ORDER BY nv.changed_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [
                {
                    "id": row[0],
                    "node_id": row[1],
                    "version": row[2],
                    "content": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                    "changed_at": row[5],
                    "change_type": row[6],
                    "node_title": row[7],
                    "node_type": row[8],
                }
                for row in cursor.fetchall()
            ]

    def diff_versions(self, node_id: str, v1: int, v2: int) -> dict[str, Any]:
        """Compare two versions of a node.

        Args:
            node_id: ID of the node
            v1: First version number
            v2: Second version number

        Returns:
            Dictionary describing the differences
        """
        ver1 = self.get_version(node_id, v1)
        ver2 = self.get_version(node_id, v2)

        if ver1 is None or ver2 is None:
            missing = []
            if ver1 is None:
                missing.append(v1)
            if ver2 is None:
                missing.append(v2)
            return {"error": f"Version(s) not found: {missing}"}

        content_changed = ver1["content"] != ver2["content"]
        metadata_changed = ver1["metadata"] != ver2["metadata"]

        # Compute metadata key differences
        meta1_keys = set(ver1["metadata"].keys())
        meta2_keys = set(ver2["metadata"].keys())

        return {
            "node_id": node_id,
            "v1": v1,
            "v2": v2,
            "content_changed": content_changed,
            "content_v1": ver1["content"],
            "content_v2": ver2["content"],
            "metadata_changed": metadata_changed,
            "metadata_keys_added": sorted(meta2_keys - meta1_keys),
            "metadata_keys_removed": sorted(meta1_keys - meta2_keys),
            "metadata_keys_common": sorted(meta1_keys & meta2_keys),
            "changed_at_v1": ver1["changed_at"],
            "changed_at_v2": ver2["changed_at"],
        }
