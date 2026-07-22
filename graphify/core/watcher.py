"""
File-system watcher for automatic graph rebuilds.

Uses ``watchdog`` (if installed) to monitor a project directory and
trigger incremental re-scans when files change.  Falls back to a
simple polling loop if watchdog is unavailable.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable

from graphify.core.config import GraphifyConfig
from graphify.core.exceptions import WatchError
from graphify.core.schema import Language, classify_language

logger = logging.getLogger(__name__)

# Debounce window — aggregate rapid file changes into one rebuild
_DEBOUNCE_SECONDS = 2.0


class FileWatcher:
    """Watch a directory for changes and trigger incremental scans."""

    def __init__(
        self,
        root_path: str,
        config: GraphifyConfig | None = None,
        on_change: Callable | None = None,
    ) -> None:
        self._root = os.path.normpath(os.path.abspath(root_path))
        if not os.path.isdir(self._root):
            raise WatchError(f"Not a directory: {self._root}")

        self._config = config or GraphifyConfig()
        self._on_change = on_change
        self._stop_event = threading.Event()
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._last_flush = 0.0
        self._observer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start watching in a background thread."""
        try:
            self._start_watchdog()
        except ImportError:
            logger.warning("watchdog not installed — falling back to polling")
            self._start_polling()

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        self._stop_event.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
        logger.info("File watcher stopped")

    @property
    def is_running(self) -> bool:
        """True if the watcher is active."""
        return not self._stop_event.is_set()

    # ------------------------------------------------------------------
    # Watchdog-based watcher
    # ------------------------------------------------------------------

    def _start_watchdog(self) -> None:
        from watchdog.events import (  # noqa: C0415  # pylint: disable=import-error
            FileSystemEventHandler,
        )
        from watchdog.observers import Observer  # noqa: C0415  # pylint: disable=import-error

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                if event.is_directory:
                    return
                path = getattr(event, "src_path", "")
                if path and watcher._is_relevant(path):
                    watcher._enqueue(path)

        self._observer = Observer()
        self._observer.schedule(_Handler(), self._root, recursive=True)  # type: ignore[attr-defined]
        self._observer.start()  # type: ignore[attr-defined]

        # Background flush thread
        flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        flush_thread.start()

        logger.info("Watching %s (watchdog)", self._root)

    # ------------------------------------------------------------------
    # Polling fallback
    # ------------------------------------------------------------------

    def _start_polling(self) -> None:
        """Poll every 3 seconds for file changes (fallback)."""
        poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        poll_thread.start()
        logger.info("Watching %s (polling)", self._root)

    def _poll_loop(self) -> None:
        mtimes: dict[str, float] = {}
        while not self._stop_event.is_set():
            try:
                for dirpath, _, filenames in os.walk(self._root):
                    for fname in filenames:
                        full = os.path.join(dirpath, fname)
                        if not self._is_relevant(full):
                            continue
                        try:
                            mtime = os.path.getmtime(full)
                        except OSError:
                            continue
                        if full not in mtimes:
                            mtimes[full] = mtime
                        elif mtimes[full] != mtime:
                            mtimes[full] = mtime
                            self._enqueue(full)
            except OSError as exc:
                logger.warning("Poll error: %s", exc)
            self._stop_event.wait(3.0)

    # ------------------------------------------------------------------
    # Change aggregation
    # ------------------------------------------------------------------

    def _enqueue(self, path: str) -> None:
        """Add a changed file to the pending set."""
        with self._lock:
            rel = os.path.relpath(path, self._root)
            self._pending.add(rel)

    def _flush_loop(self) -> None:
        """Periodically flush pending changes after debounce window."""
        while not self._stop_event.is_set():
            self._stop_event.wait(_DEBOUNCE_SECONDS)
            self._flush()

    def _flush(self) -> None:
        """Trigger callback with accumulated changes."""
        with self._lock:
            if not self._pending:
                return
            changed = set(self._pending)
            self._pending.clear()

        logger.info("Detected %d changed file(s)", len(changed))
        if self._on_change:
            try:
                self._on_change(changed)
            except Exception:
                logger.exception("Error in change callback")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_relevant(self, path: str) -> bool:
        """Check if a file should trigger a rebuild."""
        rel = os.path.relpath(path, self._root)
        # Skip hidden dirs/files
        parts = rel.split(os.sep)
        if any(p.startswith(".") for p in parts):
            return False
        # Skip common non-source dirs
        skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"}
        if any(p in skip_dirs for p in parts):
            return False
        # Only source files
        lang = classify_language(rel)
        return lang != Language.UNKNOWN
