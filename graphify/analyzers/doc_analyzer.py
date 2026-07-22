"""
Documentation analyzer — extracts structure from Markdown, RST, and

plain-text documentation files.
"""

from __future__ import annotations

import hashlib
import re

from graphify.analyzers.base import AnalysisResult, BaseAnalyzer
from graphify.core.schema import Edge, EdgeType, Node, NodeType

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_RST_HEADING_RE = re.compile(r"^(.+)\n([=\-~^\"]+)$", re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r"```(\w+)?", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class DocAnalyzer(BaseAnalyzer):
    """Analyzer for documentation files (Markdown, RST)."""

    def analyze(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        """Analyze a documentation file and extract concepts."""
        nodes: list[Node] = []
        edges: list[Edge] = []

        is_rst = file_path.endswith(".rst")

        # Extract headings → DOCUMENTATION nodes
        if is_rst:
            headings = self._extract_rst_headings(source)
        else:
            headings = self._extract_md_headings(source)

        for level, title, line in headings:
            doc_id = _make_id(project_id, "doc", f"{file_path}:{line}:{title}")
            nodes.append(
                Node(
                    id=doc_id,
                    node_type=NodeType.DOCUMENTATION,
                    name=title,
                    qualified_name=f"{file_path}#{title.lower().replace(' ', '-')}",
                    file_path=file_path,
                    language="markdown",
                    line_start=line,
                    content=title,
                    metadata={"level": level},
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=doc_id,
                    edge_type=EdgeType.CONTAINS,
                    project_id=project_id,
                )
            )

        # Extract code blocks to note referenced languages
        languages_used = set()
        for match in _CODE_BLOCK_RE.finditer(source):
            lang = match.group(1)
            if lang:
                languages_used.add(lang)

        if languages_used:
            meta_id = _make_id(project_id, "doc-meta", file_path)
            nodes.append(
                Node(
                    id=meta_id,
                    node_type=NodeType.DOCUMENTATION,
                    name=f"Code examples in {file_path}",
                    file_path=file_path,
                    language="markdown",
                    content=f"Code blocks: {', '.join(sorted(languages_used))}",
                    metadata={"code_languages": sorted(languages_used)},
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=meta_id,
                    edge_type=EdgeType.DOCUMENTS,
                    project_id=project_id,
                )
            )

        return AnalysisResult(nodes=nodes, edges=edges)

    @staticmethod
    def _extract_md_headings(source: str) -> list[tuple]:
        """Return (level, title, line_number) for Markdown headings."""
        results = []
        for match in _MD_HEADING_RE.finditer(source):
            level = len(match.group(1))
            title = match.group(2).strip()
            line = source[: match.start()].count("\n") + 1
            results.append((level, title, line))
        return results

    @staticmethod
    def _extract_rst_headings(source: str) -> list[tuple]:
        """Return (level, title, line_number) for RST headings."""
        results = []
        underline_chars = "=-~^\"'"
        for match in _RST_HEADING_RE.finditer(source):
            title = match.group(1).strip()
            underline = match.group(2)
            if len(underline) >= len(title) and underline[0] in underline_chars:
                level = underline_chars.index(underline[0]) + 1
                line = source[: match.start()].count("\n") + 1
                results.append((level, title, line))
        return results


def _make_id(project_id: str, prefix: str, name: str) -> str:
    raw = f"{project_id}:{prefix}:{name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
