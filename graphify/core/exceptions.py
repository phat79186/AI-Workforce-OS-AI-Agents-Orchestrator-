"""
Custom exception hierarchy for the Graphify system.

All Graphify exceptions inherit from :class:`GraphifyError`, enabling
callers to catch all Graphify-related errors with a single handler
while still distinguishing specific failure modes.
"""

from __future__ import annotations


class GraphifyError(Exception):
    """Base exception for all Graphify errors."""

    def __init__(self, message: str = "", *, code: str = "GRAPHIFY_ERROR") -> None:  # noqa: B042
        self.code = code
        super().__init__(message)


# ------------------------------------------------------------------
# Scanning & analysis
# ------------------------------------------------------------------


class ScanError(GraphifyError):
    """Raised when a directory scan fails."""

    def __init__(self, message: str = "", *, path: str = "") -> None:  # noqa: B042
        self.path = path
        super().__init__(message, code="SCAN_ERROR")


class AnalysisError(GraphifyError):
    """Raised when a file analysis fails."""

    def __init__(  # noqa: B042
        self,
        message: str = "",
        *,
        file_path: str = "",
        analyzer: str = "",
    ) -> None:
        self.file_path = file_path
        self.analyzer = analyzer
        super().__init__(message, code="ANALYSIS_ERROR")


# ------------------------------------------------------------------
# Graph store
# ------------------------------------------------------------------


class GraphError(GraphifyError):
    """Raised on graph store I/O or integrity failures."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="GRAPH_ERROR")


class SchemaVersionError(GraphError):
    """Database schema version mismatch."""

    def __init__(self, expected: int, actual: int) -> None:  # noqa: B042
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Schema version mismatch: expected {expected}, found {actual}. "
            "Run migrations or recreate the database."
        )


class NodeNotFoundError(GraphError):
    """Referenced node does not exist."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"Node not found: {node_id}")


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


class ConfigError(GraphifyError):
    """Invalid or missing configuration."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="CONFIG_ERROR")


# ------------------------------------------------------------------
# Export & rendering
# ------------------------------------------------------------------


class ExportError(GraphifyError):
    """Raised when graph export fails."""

    def __init__(self, message: str = "", *, fmt: str = "") -> None:  # noqa: B042
        self.format = fmt
        super().__init__(message, code="EXPORT_ERROR")


class RenderError(GraphifyError):
    """Raised when visualization rendering fails."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="RENDER_ERROR")


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class ValidationError(GraphifyError):
    """Input data fails validation."""

    def __init__(self, message: str = "", *, field: str = "") -> None:  # noqa: B042
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR")


class PathTraversalError(ValidationError):
    """Attempt to access a path outside the allowed scope."""

    def __init__(self, path: str, root: str) -> None:  # noqa: B042
        self.path = path
        self.root = root
        super().__init__(
            f"Path traversal blocked: {path!r} escapes root {root!r}",
            field="path",
        )


# ------------------------------------------------------------------
# Watch mode
# ------------------------------------------------------------------


class WatchError(GraphifyError):
    """Raised when the file-system watcher encounters an error."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="WATCH_ERROR")
