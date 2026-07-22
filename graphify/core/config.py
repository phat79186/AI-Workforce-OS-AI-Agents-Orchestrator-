"""
Graphify configuration.

All tunables live here with sensible defaults.  Override via constructor kwargs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GraphifyConfig:
    """Immutable configuration for a graphify scan."""

    # --- Scanning limits ---------------------------------------------------
    max_files: int = 10_000
    max_file_size_bytes: int = 2 * 1024 * 1024  # 2 MB
    max_depth: int = 30

    # --- Database -----------------------------------------------------------
    db_path: str = ""  # empty → in-memory; set to file path for persistence

    # --- Directories to skip ------------------------------------------------
    skip_dirs: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".git",
                ".hg",
                ".svn",
                "__pycache__",
                ".mypy_cache",
                ".pytest_cache",
                "node_modules",
                ".venv",
                "venv",
                "env",
                ".env",
                ".tox",
                ".nox",
                "dist",
                "build",
                "egg-info",
                ".egg-info",
                ".eggs",
                "htmlcov",
                ".coverage",
                "coverage",
                ".cache",
                ".idea",
                ".vscode",
                ".vs",
                ".fleet",
                ".DS_Store",
                "Thumbs.db",
                "vendor",
                "target",
                "bin",
                "obj",
            }
        )
    )

    # --- Files to skip (glob-style basenames) --------------------------------
    skip_files: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".DS_Store",
                "Thumbs.db",
                "desktop.ini",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
                "poetry.lock",
                "Pipfile.lock",
                "Cargo.lock",
                "go.sum",
            }
        )
    )

    # --- Binary extensions to skip -------------------------------------------
    binary_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".bmp",
                ".ico",
                ".svg",
                ".webp",
                ".mp3",
                ".mp4",
                ".avi",
                ".mov",
                ".wav",
                ".flac",
                ".zip",
                ".tar",
                ".gz",
                ".bz2",
                ".xz",
                ".7z",
                ".rar",
                ".woff",
                ".woff2",
                ".ttf",
                ".eot",
                ".otf",
                ".pdf",
                ".doc",
                ".docx",
                ".xls",
                ".xlsx",
                ".ppt",
                ".pptx",
                ".so",
                ".dll",
                ".dylib",
                ".o",
                ".a",
                ".lib",
                ".pyc",
                ".pyo",
                ".class",
                ".jar",
                ".exe",
                ".bin",
                ".dat",
                ".db",
                ".sqlite",
                ".sqlite3",
            }
        )
    )

    # --- Concurrency --------------------------------------------------------
    worker_threads: int = 4

    # --- Features -----------------------------------------------------------
    extract_call_graph: bool = True
    extract_rationale: bool = True
    use_cache: bool = True
    generate_report: bool = True
    generate_html: bool = True

    # --- Logging ------------------------------------------------------------
    verbose: bool = False

    def resolve_db_path(self, project_path: str) -> str:
        """Return resolved DB path, defaulting to ``<project>/.graphify.db``."""
        if self.db_path:
            return self.db_path
        return os.path.join(project_path, ".graphify.db")
