"""
Input validation utilities for Graphify.

Provides path safety checks, parameter validation, and sanitization
to prevent path traversal, injection, and invalid input.
"""

from __future__ import annotations

import os
import re

from graphify.core.exceptions import PathTraversalError, ValidationError


def validate_path(path: str, root: str | None = None) -> str:
    """Normalize and validate a file path.

    If *root* is provided, ensures the resolved path stays within it.
    Returns the normalized absolute path.
    """
    if not path or not path.strip():
        raise ValidationError("Path must not be empty", field="path")

    resolved = os.path.normpath(os.path.abspath(path))

    if root:
        root_resolved = os.path.normpath(os.path.abspath(root))
        if not resolved.startswith(root_resolved + os.sep) and resolved != root_resolved:
            raise PathTraversalError(path, root)

    return resolved


def validate_project_id(project_id: str) -> str:
    """Validate a project ID (hex SHA-256 prefix)."""
    if not project_id:
        return ""
    if not re.match(r"^[a-f0-9]{12,64}$", project_id):
        raise ValidationError(
            f"Invalid project_id: {project_id!r} (expected hex string)",
            field="project_id",
        )
    return project_id


def validate_positive_int(value: int, name: str, max_val: int = 100_000) -> int:
    """Ensure an integer is positive and within bounds."""
    if not isinstance(value, int) or value < 1:
        raise ValidationError(f"{name} must be a positive integer, got {value}", field=name)
    if value > max_val:
        raise ValidationError(f"{name} must be ≤ {max_val}, got {value}", field=name)
    return value


def validate_node_name(name: str) -> str:
    """Validate a node name query."""
    if not name or not name.strip():
        raise ValidationError("Node name must not be empty", field="name")
    if len(name) > 500:
        raise ValidationError("Node name too long (max 500 chars)", field="name")
    return name.strip()


def sanitize_search_query(query: str) -> str:
    """Sanitize an FTS5 search query to prevent injection."""
    if not query or not query.strip():
        raise ValidationError("Search query must not be empty", field="query")
    # Remove FTS5 special syntax that could be exploited
    cleaned = re.sub(r'["\'\\\x00]', " ", query)
    return cleaned.strip()[:1000]
