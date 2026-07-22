"""
.graphifyignore parser — gitignore-style pattern matching.

Reads a ``.graphifyignore`` file from the project root and filters
file paths using the same semantics as ``.gitignore``:
  - Blank lines and ``#`` comments are ignored.
  - Trailing ``/`` matches directories only.
  - ``*`` matches within a path segment; ``**`` matches across segments.
  - Leading ``!`` negates a pattern (un-ignore).
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Pattern type: (is_negation, compiled_regex, raw_pattern)
_CompiledPattern = Tuple[bool, re.Pattern, str]


class IgnoreFilter:
    """Evaluates paths against .graphifyignore rules."""

    def __init__(self, root_path: str) -> None:
        self._root = root_path
        self._patterns: list[_CompiledPattern] = []
        self._load()

    @property
    def has_rules(self) -> bool:
        """True if any ignore rules were loaded."""
        return len(self._patterns) > 0

    def is_ignored(self, rel_path: str) -> bool:
        """Return True if *rel_path* should be excluded.

        Patterns are evaluated in order; last matching pattern wins.
        """
        if not self._patterns:
            return False

        # Normalise to forward slashes for consistent matching
        normalized = rel_path.replace(os.sep, "/")
        ignored = False

        for is_negation, pattern, _raw in self._patterns:
            if pattern.search(normalized):
                ignored = not is_negation

        return ignored

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        ignore_file = os.path.join(self._root, ".graphifyignore")
        if not os.path.isfile(ignore_file):
            return

        try:
            with open(ignore_file, encoding="utf-8") as fh:
                for line in fh:
                    line = line.rstrip("\n\r")
                    compiled = self._parse_line(line)
                    if compiled is not None:
                        self._patterns.append(compiled)
        except OSError:
            logger.warning("Could not read .graphifyignore at %s", ignore_file)
            return

        logger.info(
            "Loaded %d ignore patterns from %s",
            len(self._patterns),
            ignore_file,
        )

    @staticmethod
    def _parse_line(line: str) -> _CompiledPattern | None:
        """Parse a single gitignore-style line into a compiled pattern."""
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None

        is_negation = False
        if stripped.startswith("!"):
            is_negation = True
            stripped = stripped[1:]

        # Directory-only patterns (trailing /)
        dir_only = stripped.endswith("/")
        if dir_only:
            stripped = stripped.rstrip("/")

        regex = _glob_to_regex(stripped, dir_only=dir_only)
        return is_negation, re.compile(regex), line


def _glob_to_regex(pattern: str, dir_only: bool = False) -> str:
    """Convert a gitignore glob pattern to a regex string.

    Handles ``*``, ``**``, ``?``, and character classes.
    """
    # If pattern has no slash (except trailing), match basename anywhere
    if "/" not in pattern:
        # Match this name as a path segment anywhere
        base = fnmatch.translate(pattern)
        # fnmatch.translate anchors with \Z; we want to match within path
        base = base.replace(r"\Z", "").replace(r"\z", "")
        if dir_only:
            return rf"(^|/)({base})(/|$)"
        return rf"(^|/)({base})($|/)"

    # Pattern has explicit path separators
    parts = pattern.split("/")
    regex_parts = []
    for part in parts:
        if part == "**":
            regex_parts.append(".*")
        else:
            translated = fnmatch.translate(part)
            translated = translated.replace(r"\Z", "").replace(r"\z", "")
            regex_parts.append(translated)

    joined = "/".join(regex_parts)
    if dir_only:
        return rf"(^|/)({joined})(/|$)"
    return rf"(^|/)?({joined})($|/)"
