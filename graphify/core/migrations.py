"""
Database schema migration system for Graphify.

Tracks schema versions in a ``schema_meta`` table and applies forward
migrations sequentially.  Each migration is a pure function that
receives a ``sqlite3.Connection`` and transforms the schema in place.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Migration registry
# ------------------------------------------------------------------

_MIGRATIONS: dict[int, Callable] = {}


def _register(version: int):
    """Decorator that registers a migration function for *version*."""

    def decorator(fn):
        _MIGRATIONS[version] = fn
        return fn

    return decorator


# ------------------------------------------------------------------
# Individual migrations
# ------------------------------------------------------------------


@_register(2)
def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Add confidence and provenance columns to edges table."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(edges)").fetchall()}
    if "confidence" not in cols:
        conn.execute("ALTER TABLE edges ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0")
    if "provenance" not in cols:
        conn.execute("ALTER TABLE edges ADD COLUMN provenance TEXT NOT NULL DEFAULT 'EXTRACTED'")
    logger.info("Migration v1→v2: added confidence/provenance columns")


@_register(3)
def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """Add metrics and snapshots tables for scan tracking."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scan_metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT NOT NULL,
            scanned_at  REAL NOT NULL,
            duration_s  REAL NOT NULL,
            files_total INTEGER NOT NULL DEFAULT 0,
            files_changed INTEGER NOT NULL DEFAULT 0,
            files_cached INTEGER NOT NULL DEFAULT 0,
            nodes_added INTEGER NOT NULL DEFAULT 0,
            nodes_removed INTEGER NOT NULL DEFAULT 0,
            edges_added INTEGER NOT NULL DEFAULT 0,
            edges_removed INTEGER NOT NULL DEFAULT 0,
            cache_hit_rate REAL NOT NULL DEFAULT 0.0,
            analyzer_ms TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_project
            ON scan_metrics(project_id);

        CREATE TABLE IF NOT EXISTS graph_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT NOT NULL,
            created_at  REAL NOT NULL,
            node_count  INTEGER NOT NULL DEFAULT 0,
            edge_count  INTEGER NOT NULL DEFAULT 0,
            node_ids    TEXT NOT NULL DEFAULT '[]',
            edge_ids    TEXT NOT NULL DEFAULT '[]',
            label       TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_project
            ON graph_snapshots(project_id);
    """)
    logger.info("Migration v2→v3: added scan_metrics and graph_snapshots tables")


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

LATEST_VERSION = max(_MIGRATIONS.keys()) if _MIGRATIONS else 1


def get_current_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version from the database."""
    try:
        row = conn.execute(
            "SELECT version FROM schema_meta ORDER BY version DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else 1
    except sqlite3.OperationalError:
        return 1


def ensure_meta_table(conn: sqlite3.Connection) -> None:
    """Create the ``schema_meta`` table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            version     INTEGER PRIMARY KEY,
            applied_at  REAL NOT NULL,
            description TEXT NOT NULL DEFAULT ''
        )
    """)


def migrate(conn: sqlite3.Connection, target: int | None = None) -> int:
    """Apply all pending migrations up to *target* (default: latest).

    Returns the final schema version after migration.
    """
    import time  # noqa: C0415 — avoid top-level for lightweight import

    ensure_meta_table(conn)
    current = get_current_version(conn)
    target = target or LATEST_VERSION

    if current >= target:
        logger.debug("Schema already at version %d (target %d)", current, target)
        return current

    for version in sorted(_MIGRATIONS):
        if version <= current:
            continue
        if version > target:
            break

        logger.info("Applying migration to v%d …", version)
        _MIGRATIONS[version](conn)
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (version, applied_at, description) VALUES (?, ?, ?)",
            (version, time.time(), f"Migration to v{version}"),
        )
        conn.commit()
        current = version

    logger.info("Schema migration complete: now at v%d", current)
    return current
