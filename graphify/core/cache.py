"""
Content-addressable cache for incremental re-scans.

Stores SHA-256 hashes of file contents so that re-runs skip unchanged
files.  The cache is stored alongside the graph in the same SQLite DB.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from collections.abc import Callable

logger = logging.getLogger(__name__)


class ContentCache:
    """SHA-256 content cache backed by the graph's SQLite DB."""

    def __init__(self, conn_factory: Callable[[], sqlite3.Connection]) -> None:
        """Accept a callable that returns the thread-local sqlite3.Connection."""
        self._conn = conn_factory
        self._ensure_table()

    def _ensure_table(self) -> None:
        conn = self._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_cache (
                file_path   TEXT NOT NULL,
                project_id  TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                file_size   INTEGER NOT NULL DEFAULT 0,
                cached_at   REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (file_path, project_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_project ON file_cache(project_id)")
        conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_hash(self, file_path: str, project_id: str) -> str | None:
        """Return the cached SHA-256 for *file_path*, or ``None``."""
        row = (
            self._conn()
            .execute(
                "SELECT content_hash FROM file_cache WHERE file_path = ? AND project_id = ?",
                (file_path, project_id),
            )
            .fetchone()
        )
        return row[0] if row else None

    def get_all_hashes(self, project_id: str) -> dict[str, str]:
        """Return ``{file_path: hash}`` for every cached file in the project."""
        rows = (
            self._conn()
            .execute(
                "SELECT file_path, content_hash FROM file_cache WHERE project_id = ?",
                (project_id,),
            )
            .fetchall()
        )
        return {r[0]: r[1] for r in rows}

    def set_hash(
        self,
        file_path: str,
        project_id: str,
        content_hash: str,
        file_size: int = 0,
    ) -> None:
        """Upsert the hash for *file_path*."""
        import time  # pylint: disable=C0415

        self._conn().execute(
            """INSERT INTO file_cache (file_path, project_id, content_hash, file_size, cached_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(file_path, project_id) DO UPDATE SET
                   content_hash=excluded.content_hash,
                   file_size=excluded.file_size,
                   cached_at=excluded.cached_at""",
            (file_path, project_id, content_hash, file_size, time.time()),
        )
        self._conn().commit()

    def set_hashes_bulk(
        self,
        entries: dict[str, str],
        project_id: str,
    ) -> None:
        """Bulk-upsert ``{file_path: hash}``."""
        import time  # pylint: disable=C0415

        now = time.time()
        self._conn().executemany(
            """INSERT INTO file_cache (file_path, project_id, content_hash, file_size, cached_at)
               VALUES (?, ?, ?, 0, ?)
               ON CONFLICT(file_path, project_id) DO UPDATE SET
                   content_hash=excluded.content_hash,
                   cached_at=excluded.cached_at""",
            [(fp, project_id, h, now) for fp, h in entries.items()],
        )
        self._conn().commit()

    def remove_paths(self, file_paths: set[str], project_id: str) -> int:
        """Delete cache entries for removed files. Returns count deleted."""
        if not file_paths:
            return 0
        conn = self._conn()
        placeholders = ",".join("?" for _ in file_paths)
        cursor = conn.execute(
            f"DELETE FROM file_cache WHERE project_id = ? AND file_path IN ({placeholders})",
            [project_id, *file_paths],
        )
        conn.commit()
        return cursor.rowcount

    def clear_project(self, project_id: str) -> int:
        """Remove all cache entries for a project."""
        cursor = self._conn().execute(
            "DELETE FROM file_cache WHERE project_id = ?",
            (project_id,),
        )
        self._conn().commit()
        return cursor.rowcount

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def hash_content(content: str) -> str:
        """Compute SHA-256 hex digest for file content."""
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    @staticmethod
    def hash_file(file_path: str) -> str:
        """Read a file as text and return its SHA-256 hex digest.

        Uses the same text-mode read (utf-8, errors=replace) as
        :meth:`hash_content` so that hashes are consistent between
        the diff-cache comparison and the analysis phase.
        """
        try:
            with open(file_path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            # Fall back to binary for unreadable-as-text files
            h = hashlib.sha256()
            with open(file_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
