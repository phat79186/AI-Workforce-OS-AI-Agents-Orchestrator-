"""
Generic analyzer — extracts basic structure from languages without

a dedicated AST parser (Go, Rust, Java, C/C++, etc.) using regex.
"""

from __future__ import annotations

import hashlib
import re

from graphify.analyzers.base import AnalysisResult, BaseAnalyzer
from graphify.core.schema import Edge, EdgeType, Node, NodeType

# Patterns that work reasonably well across C-family languages
_CLASS_LIKE_RE = re.compile(
    r"^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?(?:class|struct|interface|enum)\s+(\w+)",
    re.MULTILINE,
)
_FUNC_LIKE_RE = re.compile(
    r"^(?:pub\s+)?(?:async\s+)?(?:fn|func|def|function|sub)\s+(\w+)\s*[(<]",
    re.MULTILINE,
)
_GO_FUNC_RE = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.MULTILINE)


class GenericAnalyzer(BaseAnalyzer):
    """Regex fallback analyzer for unsupported languages."""

    def analyze(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        """Analyze a generic source file and extract basic structure."""
        nodes: list[Node] = []
        edges: list[Edge] = []
        lang = file_path.rsplit(".", maxsplit=1)[-1] if "." in file_path else "unknown"

        # Classes / structs
        for match in _CLASS_LIKE_RE.finditer(source):
            name = match.group(1)
            line = source[: match.start()].count("\n") + 1
            cls_id = _make_id(project_id, "cls", f"{file_path}:{name}")
            nodes.append(
                Node(
                    id=cls_id,
                    node_type=NodeType.CLASS,
                    name=name,
                    qualified_name=f"{file_path}:{name}",
                    file_path=file_path,
                    language=lang,
                    line_start=line,
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=cls_id,
                    edge_type=EdgeType.CONTAINS,
                    project_id=project_id,
                )
            )

        # Functions
        patterns = [_FUNC_LIKE_RE, _GO_FUNC_RE]
        seen = set()
        for pattern in patterns:
            for match in pattern.finditer(source):
                name = match.group(1)
                if name in seen:
                    continue
                seen.add(name)
                line = source[: match.start()].count("\n") + 1
                fn_id = _make_id(project_id, "fn", f"{file_path}:{name}")
                nodes.append(
                    Node(
                        id=fn_id,
                        node_type=NodeType.FUNCTION,
                        name=name,
                        qualified_name=f"{file_path}:{name}",
                        file_path=file_path,
                        language=lang,
                        line_start=line,
                        project_id=project_id,
                    )
                )
                edges.append(
                    Edge(
                        source_id=file_node_id,
                        target_id=fn_id,
                        edge_type=EdgeType.CONTAINS,
                        project_id=project_id,
                    )
                )

        return AnalysisResult(nodes=nodes, edges=edges)


def _make_id(project_id: str, prefix: str, name: str) -> str:
    raw = f"{project_id}:{prefix}:{name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
