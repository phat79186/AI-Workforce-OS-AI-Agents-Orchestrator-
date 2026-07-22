"""
Context Analytics - Advanced analytics and metrics for context graph.

Provides insights into context usage, patterns, and performance.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from orchestrator.context.store.graph_store import GraphStore


class ContextAnalytics:
    """Analytics engine for context graph."""

    def __init__(self, graph_store: GraphStore):
        """Initialize analytics.

        Args:
            graph_store: Graph store instance
        """
        self.logger = logging.getLogger("context.analytics")
        self.graph_store = graph_store

    def get_node_distribution(self) -> dict[str, int]:
        """Get distribution of nodes by type.

        Returns:
            Dict mapping node type to count
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT node_type, COUNT(*) as count
                FROM nodes
                GROUP BY node_type
                ORDER BY count DESC
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_edge_distribution(self) -> dict[str, int]:
        """Get distribution of edges by type.

        Returns:
            Dict mapping edge type to count
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT edge_type, COUNT(*) as count
                FROM edges
                GROUP BY edge_type
                ORDER BY count DESC
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_temporal_growth(self, days: int = 30) -> list[dict[str, Any]]:
        """Get node creation over time.

        Args:
            days: Number of days to analyze

        Returns:
            List of daily node counts
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM nodes
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY day
            """,
                [cutoff.isoformat()],
            )

            return [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

    def get_success_rate_by_agent(self) -> dict[str, dict[str, Any]]:
        """Get success rate statistics by agent.

        Returns:
            Dict mapping agent name to success stats
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT
                    json_extract(metadata, '$.agents_involved') as agents,
                    json_extract(metadata, '$.success') as success,
                    COUNT(*) as count
                FROM nodes
                WHERE node_type = 'task'
                AND json_extract(metadata, '$.agents_involved') IS NOT NULL
                GROUP BY agents, success
            """)

            agent_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"total": 0, "successful": 0, "failed": 0}
            )

            for agents_json, success, count in cursor.fetchall():
                # agents_json might be a JSON array string
                # For simplicity, we'll just use it as-is
                success_bool = success in (1, "true")

                agent_stats[str(agents_json)]["total"] += count
                if success_bool:
                    agent_stats[str(agents_json)]["successful"] += count
                else:
                    agent_stats[str(agents_json)]["failed"] += count

            # Calculate success rates
            for _, stats in agent_stats.items():
                if stats["total"] > 0:
                    stats["success_rate"] = stats["successful"] / stats["total"]
                else:
                    stats["success_rate"] = 0.0

            return dict(agent_stats)

    def get_top_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most frequently stored patterns.

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of pattern nodes with usage counts
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT
                    n.id,
                    n.content,
                    n.metadata,
                    COUNT(e.id) as usage_count,
                    n.created_at
                FROM nodes n
                LEFT JOIN edges e ON e.source_id = n.id
                WHERE n.node_type = 'pattern'
                GROUP BY n.id
                ORDER BY usage_count DESC, n.created_at DESC
                LIMIT ?
            """,
                [limit],
            )

            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2],
                    "usage_count": row[3],
                    "created_at": row[4],
                }
                for row in cursor.fetchall()
            ]

    def get_top_mistakes(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most common mistakes.

        Args:
            limit: Maximum number of mistakes to return

        Returns:
            List of mistake nodes
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT
                    n.id,
                    n.content,
                    n.metadata,
                    n.created_at
                FROM nodes n
                WHERE n.node_type = 'mistake'
                ORDER BY n.created_at DESC
                LIMIT ?
            """,
                [limit],
            )

            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2],
                    "created_at": row[3],
                }
                for row in cursor.fetchall()
            ]

    def get_database_stats(self) -> dict[str, Any]:
        """Get overall database statistics.

        Returns:
            Dict with comprehensive stats
        """
        with self.graph_store._transaction() as cursor:
            # Total counts
            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM edges")
            total_edges = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM embeddings")
            total_embeddings = cursor.fetchone()[0]

            # Average importance
            cursor.execute("SELECT AVG(importance_score) FROM nodes")
            avg_importance = cursor.fetchone()[0] or 0.0

            # Oldest and newest nodes
            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM nodes")
            oldest, newest = cursor.fetchone()

            # Database size (pages * page_size)
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_bytes = page_count * page_size

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "total_embeddings": total_embeddings,
            "avg_importance": round(avg_importance, 3),
            "oldest_node": oldest,
            "newest_node": newest,
            "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "node_distribution": self.get_node_distribution(),
            "edge_distribution": self.get_edge_distribution(),
        }

    def get_agent_activity_heatmap(self, days: int = 30) -> dict[str, Any]:
        """Get agent activity heatmap data.

        Args:
            days: Number of days to analyze

        Returns:
            Heatmap data with agents and activity by day
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with self.graph_store._transaction() as cursor:
            cursor.execute(
                """
                SELECT
                    DATE(created_at) as day,
                    json_extract(metadata, '$.engine') as engine,
                    COUNT(*) as count
                FROM nodes
                WHERE created_at >= ?
                AND node_type = 'task'
                GROUP BY DATE(created_at), engine
                ORDER BY day, engine
            """,
                [cutoff.isoformat()],
            )

            heatmap_data = []
            for row in cursor.fetchall():
                heatmap_data.append(
                    {
                        "date": row[0],
                        "engine": row[1] or "unknown",
                        "activity": row[2],
                    }
                )

            return {
                "days": days,
                "data": heatmap_data,
            }

    def get_search_performance_metrics(self) -> dict[str, Any]:
        """Get search performance metrics.

        Returns:
            Dict with search-related statistics
        """
        # This would track search query performance
        # For now, return basic embedding stats

        with self.graph_store._transaction() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_embedded,
                    COUNT(DISTINCT model_name) as model_versions
                FROM embeddings
            """)
            row = cursor.fetchone()

        return {
            "total_embedded_nodes": row[0],
            "embedding_models": row[1],
            "embedding_coverage": (
                round(row[0] / max(1, self.graph_store.get_stats()["total_nodes"]) * 100, 1)
            ),
        }

    def get_comprehensive_report(self) -> dict[str, Any]:
        """Generate comprehensive analytics report.

        Returns:
            Dict with all analytics data
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": self.get_database_stats(),
            "temporal_growth": self.get_temporal_growth(30),
            "agent_success_rates": self.get_success_rate_by_agent(),
            "top_patterns": self.get_top_patterns(10),
            "top_mistakes": self.get_top_mistakes(10),
            "agent_activity": self.get_agent_activity_heatmap(30),
            "search_performance": self.get_search_performance_metrics(),
        }
