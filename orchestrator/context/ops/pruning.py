"""
Context Pruning - Intelligent context cleanup strategies.

Implements various pruning strategies to keep the context graph
manageable and relevant over time.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from orchestrator.context.store.graph_store import GraphStore


class ContextPruner:
    """Context pruning strategies for graph maintenance."""

    def __init__(self, graph_store: GraphStore):
        """Initialize pruner.

        Args:
            graph_store: Graph store instance
        """
        self.logger = logging.getLogger("context.pruning")
        self.graph_store = graph_store

    def prune_by_age(
        self,
        max_age_days: int,
        node_types: list[str] | None = None,
        min_importance: float = 0.0,
    ) -> dict[str, Any]:
        """Remove nodes older than specified age.

        Args:
            max_age_days: Maximum age in days
            node_types: Optional list of node types to prune
            min_importance: Only prune nodes below this importance

        Returns:
            Dict with pruning statistics
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        with self.graph_store._transaction() as cursor:
            # Find candidates
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = f"""  # noqa: B608
                    SELECT id FROM nodes
                    WHERE created_at < ?
                    AND importance_score < ?
                    AND node_type IN ({placeholders})
                """
                params = [cutoff_date.isoformat(), min_importance] + node_types
            else:
                query = """
                    SELECT id FROM nodes
                    WHERE created_at < ?
                    AND importance_score < ?
                """
                params = [cutoff_date.isoformat(), min_importance]

            cursor.execute(query, params)
            candidates = [row[0] for row in cursor.fetchall()]

        # Delete nodes
        deleted_count = 0
        for node_id in candidates:
            try:
                self.graph_store.delete_node(node_id)
                deleted_count += 1
            except Exception as e:
                self.logger.warning("Failed to delete node %s: %s", node_id, e)

        self.logger.info("Pruned %s nodes older than %s days", deleted_count, max_age_days)

        return {
            "strategy": "age_based",
            "candidates": len(candidates),
            "deleted": deleted_count,
            "max_age_days": max_age_days,
            "cutoff_date": cutoff_date.isoformat(),
        }

    def prune_duplicates(
        self,
        similarity_threshold: float = 0.95,
        node_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Remove duplicate nodes based on content similarity.

        Args:
            similarity_threshold: Similarity score threshold (0-1)
            node_types: Optional list of node types to check

        Returns:
            Dict with deduplication statistics
        """
        # This would require embedding comparison
        # For now, we'll do exact content matching

        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = f"""  # noqa: B608
                    SELECT id, content, node_type, created_at
                    FROM nodes
                    WHERE node_type IN ({placeholders})
                    ORDER BY created_at DESC
                """
                cursor.execute(query, node_types)
            else:
                cursor.execute("""
                    SELECT id, content, node_type, created_at
                    FROM nodes
                    ORDER BY created_at DESC
                """)

            nodes = cursor.fetchall()

        # Group by content
        seen_content: dict[str, str] = {}  # content -> oldest node_id
        duplicates = []

        for node_id, content, node_type, _ in nodes:
            key = f"{node_type}:{content}"
            if key in seen_content:
                # This is a duplicate, keep the older one
                duplicates.append(node_id)
            else:
                seen_content[key] = node_id

        # Delete duplicates
        deleted_count = 0
        for node_id in duplicates:
            try:
                self.graph_store.delete_node(node_id)
                deleted_count += 1
            except Exception as e:
                self.logger.warning("Failed to delete duplicate %s: %s", node_id, e)

        self.logger.info("Removed %s duplicate nodes", deleted_count)

        return {
            "strategy": "duplicate_removal",
            "duplicates_found": len(duplicates),
            "deleted": deleted_count,
            "similarity_threshold": similarity_threshold,
        }

    def prune_low_importance(
        self,
        importance_threshold: float = 0.3,
        min_age_days: int = 7,
        node_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Remove low-importance nodes after a minimum age.

        Args:
            importance_threshold: Importance score threshold
            min_age_days: Minimum age in days before considering
            node_types: Optional list of node types to prune

        Returns:
            Dict with pruning statistics
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=min_age_days)

        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = f"""  # noqa: B608
                    SELECT id FROM nodes
                    WHERE importance_score < ?
                    AND created_at < ?
                    AND node_type IN ({placeholders})
                """
                params = [importance_threshold, cutoff_date.isoformat()] + node_types
            else:
                query = """
                    SELECT id FROM nodes
                    WHERE importance_score < ?
                    AND created_at < ?
                """
                params = [importance_threshold, cutoff_date.isoformat()]

            cursor.execute(query, params)
            candidates = [row[0] for row in cursor.fetchall()]

        # Delete nodes
        deleted_count = 0
        for node_id in candidates:
            try:
                self.graph_store.delete_node(node_id)
                deleted_count += 1
            except Exception as e:
                self.logger.warning("Failed to delete node %s: %s", node_id, e)

        self.logger.info(
            "Pruned %s low-importance nodes (importance < %s, age > %s days)",
            deleted_count,
            importance_threshold,
            min_age_days,
        )

        return {
            "strategy": "importance_based",
            "candidates": len(candidates),
            "deleted": deleted_count,
            "importance_threshold": importance_threshold,
            "min_age_days": min_age_days,
        }

    def prune_all(
        self,
        age_days: int | None = 90,
        importance_threshold: float | None = 0.2,
        remove_duplicates: bool = True,
    ) -> dict[str, Any]:
        """Run all pruning strategies.

        Args:
            age_days: Maximum age for age-based pruning (None to skip)
            importance_threshold: Threshold for importance pruning (None to skip)
            remove_duplicates: Whether to remove duplicates

        Returns:
            Combined pruning statistics
        """
        results: dict[str, list[Any]] = {"strategies": []}

        if remove_duplicates:
            dup_result = self.prune_duplicates()
            results["strategies"].append(dup_result)

        if age_days is not None:
            age_result = self.prune_by_age(age_days, min_importance=0.5)
            results["strategies"].append(age_result)

        if importance_threshold is not None:
            imp_result = self.prune_low_importance(importance_threshold, min_age_days=7)
            results["strategies"].append(imp_result)

        results["total_deleted"] = sum(s.get("deleted", 0) for s in results["strategies"])

        self.logger.info("Completed pruning: %s nodes removed", results["total_deleted"])

        return results
