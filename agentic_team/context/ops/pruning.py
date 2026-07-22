"""
Context Pruning — Intelligent cleanup for Agentic Team Context.

Independent implementation — does NOT import from orchestrator/context.
Provides strategies to keep the context graph manageable and relevant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from agentic_team.context.store.graph_store import GraphStore


class ContextPruner:
    """Pruning strategies for the agentic team context graph."""

    def __init__(self, graph_store: GraphStore):
        """Initialize pruner.

        Args:
            graph_store: Graph store instance.
        """
        self.logger = logging.getLogger("agentic_team.context.pruning")
        self.graph_store = graph_store

    # ------------------------------------------------------------------
    # Strategy: age-based pruning
    # ------------------------------------------------------------------

    def prune_by_age(
        self,
        max_age_days: int,
        node_types: list[str] | None = None,
        min_importance: float = 0.0,
    ) -> dict[str, Any]:
        """Remove nodes older than *max_age_days*.

        Args:
            max_age_days: Maximum age in days.
            node_types: Optional list of node type strings to restrict pruning.
            min_importance: Only prune nodes with importance below this value.

        Returns:
            Statistics dict.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()

        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = (
                    f"SELECT id FROM nodes WHERE created_at < ? AND importance_score < ?"
                    f" AND node_type IN ({placeholders})"
                )  # noqa: S608
                params: list[Any] = [cutoff, min_importance] + node_types
            else:
                query = "SELECT id FROM nodes WHERE created_at < ? AND importance_score < ?"
                params = [cutoff, min_importance]

            cursor.execute(query, params)
            candidates = [row[0] for row in cursor.fetchall()]

        deleted = self._delete_nodes(candidates)
        self.logger.info("Pruned %d nodes older than %d days", deleted, max_age_days)

        return {
            "strategy": "age_based",
            "candidates": len(candidates),
            "deleted": deleted,
            "max_age_days": max_age_days,
            "cutoff_date": cutoff,
        }

    # ------------------------------------------------------------------
    # Strategy: duplicate removal
    # ------------------------------------------------------------------

    def prune_duplicates(
        self,
        node_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Remove duplicate nodes with identical content.

        Keeps the oldest copy of each (node_type, content) pair.

        Args:
            node_types: Optional list of node type strings to restrict.

        Returns:
            Statistics dict.
        """
        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = (
                    f"SELECT id, content, node_type FROM nodes"
                    f" WHERE node_type IN ({placeholders})"
                    f" ORDER BY created_at ASC"
                )  # noqa: S608
                cursor.execute(query, node_types)
            else:
                cursor.execute("SELECT id, content, node_type FROM nodes ORDER BY created_at ASC")

            rows = cursor.fetchall()

        seen: set[str] = set()
        duplicates: list[str] = []
        for row in rows:
            key = f"{row[2]}:{row[1]}"
            if key in seen:
                duplicates.append(row[0])
            else:
                seen.add(key)

        deleted = self._delete_nodes(duplicates)
        self.logger.info("Removed %d duplicate nodes", deleted)

        return {
            "strategy": "duplicate_removal",
            "duplicates_found": len(duplicates),
            "deleted": deleted,
        }

    # ------------------------------------------------------------------
    # Strategy: low-importance pruning
    # ------------------------------------------------------------------

    def prune_low_importance(
        self,
        threshold: float = 0.3,
        min_age_days: int = 7,
    ) -> dict[str, Any]:
        """Remove low-importance nodes that are at least *min_age_days* old.

        Args:
            threshold: Importance score threshold.
            min_age_days: Minimum age in days before a node is eligible.

        Returns:
            Statistics dict.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=min_age_days)).isoformat()

        with self.graph_store._transaction() as cursor:
            cursor.execute(
                "SELECT id FROM nodes WHERE importance_score < ? AND created_at < ?",
                (threshold, cutoff),
            )
            candidates = [row[0] for row in cursor.fetchall()]

        deleted = self._delete_nodes(candidates)
        self.logger.info(
            "Pruned %d low-importance nodes (threshold=%.2f, min_age=%d days)",
            deleted,
            threshold,
            min_age_days,
        )

        return {
            "strategy": "importance_based",
            "candidates": len(candidates),
            "deleted": deleted,
            "importance_threshold": threshold,
            "min_age_days": min_age_days,
        }

    # ------------------------------------------------------------------
    # Combined pruning
    # ------------------------------------------------------------------

    def prune_all(
        self,
        age_days: int = 90,
        importance_threshold: float = 0.2,
        remove_duplicates: bool = True,
    ) -> dict[str, Any]:
        """Run all pruning strategies sequentially.

        Args:
            age_days: Maximum age for age-based pruning.
            importance_threshold: Threshold for low-importance pruning.
            remove_duplicates: Whether to run duplicate removal.

        Returns:
            Combined statistics dict.
        """
        results: dict[str, Any] = {"strategies": []}

        if remove_duplicates:
            results["strategies"].append(self.prune_duplicates())

        results["strategies"].append(self.prune_by_age(age_days, min_importance=0.5))

        results["strategies"].append(
            self.prune_low_importance(threshold=importance_threshold, min_age_days=7)
        )

        results["total_deleted"] = sum(s.get("deleted", 0) for s in results["strategies"])
        self.logger.info("Completed pruning: %d nodes removed", results["total_deleted"])
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _delete_nodes(self, node_ids: list[str]) -> int:
        """Delete a batch of nodes, returning the number actually deleted."""
        deleted = 0
        for nid in node_ids:
            try:
                if self.graph_store.delete_node(nid):
                    deleted += 1
            except Exception as exc:
                self.logger.warning("Failed to delete node %s: %s", nid, exc)
        return deleted
