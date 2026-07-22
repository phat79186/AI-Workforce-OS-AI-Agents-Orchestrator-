"""
Scan metrics collector for Graphify.

Records performance statistics for each scan — duration, cache hit rates,
per-analyzer timing, and node/edge counts — enabling trend analysis and
performance monitoring over time.
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
class ScanMetrics:
    """Accumulated metrics for a single scan run."""

    project_id: str = ""
    started_at: float = 0.0
    duration_s: float = 0.0
    files_total: int = 0
    files_changed: int = 0
    files_cached: int = 0
    nodes_added: int = 0
    nodes_removed: int = 0
    edges_added: int = 0
    edges_removed: int = 0
    cache_hit_rate: float = 0.0
    analyzer_ms: dict[str, float] = field(default_factory=dict)

    def start(self) -> None:
        """Mark scan start."""
        self.started_at = time.time()

    def stop(self) -> None:
        """Mark scan end and compute duration."""
        self.duration_s = time.time() - self.started_at

    def record_analyzer(self, name: str, elapsed_ms: float) -> None:
        """Record per-analyzer timing."""
        self.analyzer_ms[name] = self.analyzer_ms.get(name, 0.0) + elapsed_ms

    def compute_cache_rate(self) -> None:
        """Compute cache hit rate from file counts."""
        if self.files_total > 0:
            self.cache_hit_rate = self.files_cached / self.files_total
        else:
            self.cache_hit_rate = 0.0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "project_id": self.project_id,
            "started_at": self.started_at,
            "duration_s": round(self.duration_s, 3),
            "files_total": self.files_total,
            "files_changed": self.files_changed,
            "files_cached": self.files_cached,
            "nodes_added": self.nodes_added,
            "nodes_removed": self.nodes_removed,
            "edges_added": self.edges_added,
            "edges_removed": self.edges_removed,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "analyzer_ms": {k: round(v, 1) for k, v in self.analyzer_ms.items()},
        }


class MetricsStore:
    """Persist and query scan metrics in the graph database."""

    def __init__(self, get_conn_fn: Callable[[], sqlite3.Connection]) -> None:
        self._get_conn = get_conn_fn

    def save(self, metrics: ScanMetrics) -> int:
        """Persist a scan metrics record.  Returns the row ID."""
        conn = self._get_conn()
        cur = conn.execute(
            """INSERT INTO scan_metrics
               (project_id, scanned_at, duration_s,
                files_total, files_changed, files_cached,
                nodes_added, nodes_removed, edges_added, edges_removed,
                cache_hit_rate, analyzer_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                metrics.project_id,
                metrics.started_at,
                metrics.duration_s,
                metrics.files_total,
                metrics.files_changed,
                metrics.files_cached,
                metrics.nodes_added,
                metrics.nodes_removed,
                metrics.edges_added,
                metrics.edges_removed,
                metrics.cache_hit_rate,
                json.dumps(metrics.analyzer_ms),
            ),
        )
        conn.commit()
        return cur.lastrowid or 0

    def history(self, project_id: str, limit: int = 50) -> list[dict]:
        """Return scan history for a project, most recent first."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM scan_metrics
               WHERE project_id = ?
               ORDER BY scanned_at DESC
               LIMIT ?""",
            (project_id, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "scanned_at": r["scanned_at"],
                "duration_s": r["duration_s"],
                "files_total": r["files_total"],
                "files_changed": r["files_changed"],
                "files_cached": r["files_cached"],
                "nodes_added": r["nodes_added"],
                "nodes_removed": r["nodes_removed"],
                "edges_added": r["edges_added"],
                "edges_removed": r["edges_removed"],
                "cache_hit_rate": r["cache_hit_rate"],
                "analyzer_ms": json.loads(r["analyzer_ms"]),
            }
            for r in rows
        ]

    def latest(self, project_id: str) -> dict | None:
        """Return the most recent scan metrics, or None."""
        history = self.history(project_id, limit=1)
        return history[0] if history else None

    def averages(self, project_id: str, last_n: int = 10) -> dict:
        """Compute average metrics over the last *n* scans."""
        records = self.history(project_id, limit=last_n)
        if not records:
            return {}
        n = len(records)
        return {
            "avg_duration_s": round(sum(r["duration_s"] for r in records) / n, 3),
            "avg_files_total": round(sum(r["files_total"] for r in records) / n, 1),
            "avg_cache_hit_rate": round(sum(r["cache_hit_rate"] for r in records) / n, 4),
            "total_scans": n,
        }
