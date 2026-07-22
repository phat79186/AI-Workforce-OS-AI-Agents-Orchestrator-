"""
Context Analytics — Metrics and insights for Agentic Team Context.

Independent implementation — does NOT import from orchestrator/context.
Provides analytics about context usage, growth, and team performance.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from agentic_team.context.store.graph_store import GraphStore


class ContextAnalytics:
    """Analytics engine for the agentic team context graph."""

    def __init__(self, graph_store: GraphStore):
        """Initialize analytics.

        Args:
            graph_store: Graph store instance.
        """
        self.logger = logging.getLogger("agentic_team.context.analytics")
        self.graph_store = graph_store

    # ------------------------------------------------------------------
    # Distribution helpers
    # ------------------------------------------------------------------

    def get_node_distribution(self) -> dict[str, int]:
        """Count nodes grouped by type.

        Returns:
            Mapping of node type to count.
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                "SELECT node_type, COUNT(*) AS cnt FROM nodes GROUP BY node_type ORDER BY cnt DESC"
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_edge_distribution(self) -> dict[str, int]:
        """Count edges grouped by type.

        Returns:
            Mapping of edge type to count.
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                "SELECT edge_type, COUNT(*) AS cnt FROM edges GROUP BY edge_type ORDER BY cnt DESC"
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    # ------------------------------------------------------------------
    # Temporal analysis
    # ------------------------------------------------------------------

    def get_temporal_growth(self, days: int = 30) -> list[dict[str, Any]]:
        """Daily node creation counts over the last *days* days.

        Args:
            days: Look-back window in days.

        Returns:
            List of ``{"date": ..., "count": ...}`` dicts.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                FROM nodes
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY day
                """,
                (cutoff,),
            )
            return [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Database-level stats
    # ------------------------------------------------------------------

    def get_database_stats(self) -> dict[str, Any]:
        """Return high-level database statistics.

        Returns:
            Dict with total_nodes, total_edges, database_size_mb,
            avg_importance, oldest_node, newest_node, and distributions.
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM edges")
            total_edges = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(importance_score) FROM nodes")
            avg_importance = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM nodes")
            oldest, newest = cursor.fetchone()

            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_bytes = page_count * page_size

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "avg_importance": round(avg_importance, 3),
            "oldest_node": oldest,
            "newest_node": newest,
            "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "node_distribution": self.get_node_distribution(),
            "edge_distribution": self.get_edge_distribution(),
        }

    # ------------------------------------------------------------------
    # Team-specific analytics
    # ------------------------------------------------------------------

    def get_team_performance(self) -> dict[str, Any]:
        """Compute team-level performance metrics from task nodes.

        Returns:
            Dict with *total_tasks*, *successful*, *failed*,
            *success_rate*, *avg_duration_ms*.
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN json_extract(extra_data, '$.success') = 1 THEN 1 ELSE 0 END) AS ok,
                    AVG(CAST(json_extract(extra_data, '$.duration_ms') AS REAL)) AS avg_dur
                FROM nodes
                WHERE node_type = 'task'
                """)
            row = cursor.fetchone()

        total = row[0] or 0
        successful = row[1] or 0
        failed = total - successful
        avg_duration = row[2] or 0.0

        return {
            "total_tasks": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / max(total, 1), 3),
            "avg_duration_ms": round(avg_duration, 1),
        }

    def get_role_activity(self) -> dict[str, int]:
        """Count activity (nodes created) per team role.

        Roles are extracted from the ``agents_involved`` extra-data field
        stored on task nodes.

        Returns:
            Mapping of role name to activity count.
        """
        role_counts: dict[str, int] = defaultdict(int)

        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT json_extract(extra_data, '$.agents_involved') AS agents
                FROM nodes
                WHERE node_type = 'task'
                AND json_extract(extra_data, '$.agents_involved') IS NOT NULL
                """)
            import json

            for (agents_raw,) in cursor.fetchall():
                if not agents_raw:
                    continue
                try:
                    agents = json.loads(agents_raw) if isinstance(agents_raw, str) else agents_raw
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(agents, list):
                    for agent in agents:
                        role_counts[str(agent)] += 1

        return dict(role_counts)

    # ------------------------------------------------------------------
    # Comprehensive report
    # ------------------------------------------------------------------

    def get_comprehensive_report(self) -> dict[str, Any]:
        """Generate a full analytics report.

        Returns:
            Dict combining all analytics sections.
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": self.get_database_stats(),
            "temporal_growth": self.get_temporal_growth(30),
            "team_performance": self.get_team_performance(),
            "role_activity": self.get_role_activity(),
        }
