"""
Graph schema — node types, edge types, and data models.

All models are plain dataclasses with no heavy dependencies so that
graphify stays lightweight and portable.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    """Types of nodes in the project graph."""

    PROJECT = "PROJECT"
    DIRECTORY = "DIRECTORY"
    FILE = "FILE"
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    IMPORT = "IMPORT"
    DEPENDENCY = "DEPENDENCY"
    CONFIG = "CONFIG"
    DOCUMENTATION = "DOCUMENTATION"
    TEST = "TEST"
    PATTERN = "PATTERN"
    VARIABLE = "VARIABLE"
    RATIONALE = "RATIONALE"
    COMMUNITY = "COMMUNITY"


class EdgeType(str, Enum):
    """Types of directed edges between nodes."""

    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    CALLS = "CALLS"
    DEPENDS_ON = "DEPENDS_ON"
    TESTS = "TESTS"
    DOCUMENTS = "DOCUMENTS"
    CONFIGURED_BY = "CONFIGURED_BY"
    EXPORTS = "EXPORTS"
    SIBLING = "SIBLING"
    MEMBER_OF = "MEMBER_OF"


class EdgeProvenance(str, Enum):
    """How an edge was discovered — enables confidence filtering."""

    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"


class Language(str, Enum):
    """Detected programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    PHP = "php"
    SHELL = "shell"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    MARKDOWN = "markdown"
    DOCKERFILE = "dockerfile"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Extension → Language mapping
# ---------------------------------------------------------------------------

EXTENSION_LANGUAGE_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".pyw": Language.PYTHON,
    ".pyi": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".rb": Language.RUBY,
    ".cpp": Language.CPP,
    ".cxx": Language.CPP,
    ".cc": Language.CPP,
    ".hpp": Language.CPP,
    ".c": Language.C,
    ".h": Language.C,
    ".cs": Language.CSHARP,
    ".swift": Language.SWIFT,
    ".kt": Language.KOTLIN,
    ".kts": Language.KOTLIN,
    ".php": Language.PHP,
    ".sh": Language.SHELL,
    ".bash": Language.SHELL,
    ".zsh": Language.SHELL,
    ".sql": Language.SQL,
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".css": Language.CSS,
    ".scss": Language.CSS,
    ".less": Language.CSS,
    ".yaml": Language.YAML,
    ".yml": Language.YAML,
    ".json": Language.JSON,
    ".toml": Language.TOML,
    ".md": Language.MARKDOWN,
    ".mdx": Language.MARKDOWN,
    ".rst": Language.MARKDOWN,
}

# Files matched by name (no extension)
FILENAME_LANGUAGE_MAP: dict[str, Language] = {
    "Dockerfile": Language.DOCKERFILE,
    "Makefile": Language.SHELL,
    "Jenkinsfile": Language.UNKNOWN,
    ".env": Language.SHELL,
    ".env.example": Language.SHELL,
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """A single node in the project graph."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    node_type: NodeType = NodeType.FILE
    name: str = ""
    qualified_name: str = ""
    file_path: str = ""
    language: str = ""
    line_start: int = 0
    line_end: int = 0
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    project_id: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def searchable_text(self) -> str:
        """Build text blob for full-text indexing."""
        parts = [self.name, self.qualified_name, self.content]
        if self.metadata:
            parts.extend(str(v) for v in self.metadata.values() if isinstance(v, str))
        return " ".join(p for p in parts if p)


@dataclass
class Edge:
    """A directed relationship between two nodes."""

    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.CONTAINS
    weight: float = 1.0
    confidence: float = 1.0
    provenance: str = EdgeProvenance.EXTRACTED.value
    metadata: dict[str, Any] = field(default_factory=dict)
    project_id: str = ""


@dataclass
class ProjectSummary:
    """Aggregated project metadata after a scan."""

    project_id: str = ""
    root_path: str = ""
    name: str = ""
    languages: dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_tests: int = 0
    dependencies: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    scanned_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_project_id(path: str) -> str:
    """Deterministic project ID from absolute path (SHA-256 prefix)."""
    import os  # pylint: disable=C0415

    normalized = os.path.normpath(os.path.abspath(path))
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def classify_language(file_path: str) -> Language:
    """Determine language from file extension or name."""
    import os  # pylint: disable=C0415

    basename = os.path.basename(file_path)
    if basename in FILENAME_LANGUAGE_MAP:
        return FILENAME_LANGUAGE_MAP[basename]

    _, ext = os.path.splitext(basename)
    return EXTENSION_LANGUAGE_MAP.get(ext.lower(), Language.UNKNOWN)
