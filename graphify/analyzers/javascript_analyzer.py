"""
JavaScript/TypeScript analyzer — regex-based extraction of classes,

functions, imports, exports, and React components.
"""

from __future__ import annotations

import hashlib
import logging
import re

from graphify.analyzers.base import AnalysisResult, BaseAnalyzer
from graphify.core.schema import Edge, EdgeType, Node, NodeType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_CLASS_RE = re.compile(
    r"^(?:export\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?",
    re.MULTILINE,
)
_FUNCTION_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
    re.MULTILINE,
)
_ARROW_CONST_RE = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",
    re.MULTILINE,
)
_REACT_COMPONENT_RE = re.compile(
    r"^(?:export\s+)?(?:const|function)\s+([A-Z]\w+)",
    re.MULTILINE,
)
_IMPORT_RE = re.compile(
    r"""import\s+(?:{[^}]+}|[\w*]+(?:\s*,\s*{[^}]+})?)\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_REQUIRE_RE = re.compile(
    r"""(?:const|let|var)\s+(?:\w+|\{[^}]+\})\s*=\s*require\(['"]([^'"]+)['"]\)""",
    re.MULTILINE,
)
_EXPORT_DEFAULT_RE = re.compile(
    r"^export\s+default\s+(?:class|function)?\s*(\w+)?",
    re.MULTILINE,
)


class JavaScriptAnalyzer(BaseAnalyzer):
    """Regex-based JavaScript/TypeScript analyzer."""

    def analyze(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        """Extract JS/TS structure via regex patterns."""
        nodes: list[Node] = []
        edges: list[Edge] = []

        is_ts = file_path.endswith((".ts", ".tsx"))
        is_test = self._is_test_file(file_path)
        lang = "typescript" if is_ts else "javascript"

        # Classes
        for match in _CLASS_RE.finditer(source):
            name = match.group(1)
            base = match.group(2) or ""
            line = source[: match.start()].count("\n") + 1
            cls_id = self._make_id(project_id, "cls", f"{file_path}:{name}")

            nodes.append(
                Node(
                    id=cls_id,
                    node_type=NodeType.CLASS,
                    name=name,
                    qualified_name=f"{file_path}:{name}",
                    file_path=file_path,
                    language=lang,
                    line_start=line,
                    metadata={"extends": base} if base else {},
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
            if base:
                base_id = self._make_id(project_id, "cls", base)
                edges.append(
                    Edge(
                        source_id=cls_id,
                        target_id=base_id,
                        edge_type=EdgeType.INHERITS,
                        project_id=project_id,
                    )
                )

        # Named functions
        seen_names = set()
        for match in _FUNCTION_RE.finditer(source):
            name = match.group(1)
            if name in seen_names:
                continue
            seen_names.add(name)
            line = source[: match.start()].count("\n") + 1
            ntype = (
                NodeType.TEST
                if is_test and (name.startswith("test") or name.startswith("it"))
                else NodeType.FUNCTION
            )

            fn_id = self._make_id(project_id, "fn", f"{file_path}:{name}")
            nodes.append(
                Node(
                    id=fn_id,
                    node_type=ntype,
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

        # Arrow function constants
        for match in _ARROW_CONST_RE.finditer(source):
            name = match.group(1)
            if name in seen_names:
                continue
            seen_names.add(name)
            line = source[: match.start()].count("\n") + 1
            fn_id = self._make_id(project_id, "fn", f"{file_path}:{name}")
            nodes.append(
                Node(
                    id=fn_id,
                    node_type=NodeType.FUNCTION,
                    name=name,
                    qualified_name=f"{file_path}:{name}",
                    file_path=file_path,
                    language=lang,
                    line_start=line,
                    metadata={"is_arrow": True},
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

        # Imports
        for pattern in (_IMPORT_RE, _REQUIRE_RE):
            for match in pattern.finditer(source):
                module = match.group(1)
                line = source[: match.start()].count("\n") + 1
                imp_id = self._make_id(project_id, "imp", f"{file_path}:{module}")
                nodes.append(
                    Node(
                        id=imp_id,
                        node_type=NodeType.IMPORT,
                        name=module,
                        qualified_name=module,
                        file_path=file_path,
                        language=lang,
                        line_start=line,
                        content=match.group(0)[:200],
                        project_id=project_id,
                    )
                )
                edges.append(
                    Edge(
                        source_id=file_node_id,
                        target_id=imp_id,
                        edge_type=EdgeType.IMPORTS,
                        project_id=project_id,
                    )
                )

        return AnalysisResult(nodes=nodes, edges=edges)

    @staticmethod
    def _make_id(project_id: str, prefix: str, name: str) -> str:
        raw = f"{project_id}:{prefix}:{name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _is_test_file(file_path: str) -> bool:
        basename = file_path.rsplit("/", maxsplit=1)[-1] if "/" in file_path else file_path
        return (
            basename.endswith(
                (
                    ".test.js",
                    ".test.ts",
                    ".test.jsx",
                    ".test.tsx",
                    ".spec.js",
                    ".spec.ts",
                    ".spec.jsx",
                    ".spec.tsx",
                )
            )
            or "/__tests__/" in file_path
            or "/test/" in file_path
        )
