"""
Python analyzer — uses the ``ast`` module to extract classes, functions,

imports, decorators, docstrings, call graphs, and rationale comments.
"""

from __future__ import annotations

import ast
import hashlib
import logging
import os
import re

from graphify.analyzers.base import AnalysisResult, BaseAnalyzer
from graphify.core.schema import Edge, EdgeType, Node, NodeType

logger = logging.getLogger(__name__)

# Rationale comment patterns (WHY, TODO, HACK, NOTE, FIXME, IMPORTANT, XXX)
_RATIONALE_RE = re.compile(
    r"#\s*(TODO|FIXME|HACK|NOTE|WHY|IMPORTANT|XXX|WARN|DEPRECATED)\b[:\s]*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)


class PythonAnalyzer(BaseAnalyzer):
    """AST-based Python source analyzer with call graph and rationale extraction."""

    def analyze(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        """Parse Python source and extract structure."""
        nodes: list[Node] = []
        edges: list[Edge] = []

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            logger.debug("Syntax error in %s, skipping AST analysis", file_path)
            return AnalysisResult()

        is_test = self._is_test_file(file_path)
        module_name = self._path_to_module(file_path)

        # Track defined names for intra-file call resolution
        defined_names: set[str] = set()

        # Walk top-level and nested definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_nodes, cls_edges = self._extract_class(
                    node,
                    file_path,
                    file_node_id,
                    project_id,
                    module_name,
                    is_test,
                )
                nodes.extend(cls_nodes)
                edges.extend(cls_edges)
                defined_names.add(node.name)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        defined_names.add(f"{node.name}.{item.name}")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._is_top_level(tree, node):
                    fn_node, fn_edges = self._extract_function(
                        node,
                        file_path,
                        file_node_id,
                        project_id,
                        module_name,
                        is_test,
                    )
                    nodes.append(fn_node)
                    edges.extend(fn_edges)
                    defined_names.add(node.name)

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imp_nodes, imp_edges = self._extract_import(
                    node,
                    file_path,
                    file_node_id,
                    project_id,
                )
                nodes.extend(imp_nodes)
                edges.extend(imp_edges)

        # Extract call graph edges
        call_edges = self._extract_call_graph(
            tree,
            file_path,
            file_node_id,
            project_id,
            module_name,
            defined_names,
        )
        edges.extend(call_edges)

        # Extract rationale comments
        rationale_nodes, rationale_edges = self._extract_rationale(
            source,
            file_path,
            file_node_id,
            project_id,
        )
        nodes.extend(rationale_nodes)
        edges.extend(rationale_edges)

        return AnalysisResult(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # Class extraction
    # ------------------------------------------------------------------

    def _extract_class(
        self,
        node: ast.ClassDef,
        file_path: str,
        file_node_id: str,
        project_id: str,
        module_name: str,
        is_test: bool,
    ) -> tuple[list[Node], list[Edge]]:
        """Extract a class definition and its methods."""
        nodes: list[Node] = []
        edges: list[Edge] = []

        qualified = f"{module_name}.{node.name}" if module_name else node.name
        cls_id = self._make_id(project_id, "cls", qualified)
        docstring = ast.get_docstring(node) or ""

        bases = [self._name_from_expr(b) for b in node.bases]
        decorators = [self._name_from_expr(d) for d in node.decorator_list]

        ntype = NodeType.TEST if is_test and node.name.startswith("Test") else NodeType.CLASS

        cls_node = Node(
            id=cls_id,
            node_type=ntype,
            name=node.name,
            qualified_name=qualified,
            file_path=file_path,
            language="python",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            content=docstring[:1000],
            metadata={
                "bases": bases,
                "decorators": decorators,
                "method_count": sum(
                    1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ),
            },
            project_id=project_id,
        )
        nodes.append(cls_node)

        # CONTAINS edge from file
        edges.append(
            Edge(
                source_id=file_node_id,
                target_id=cls_id,
                edge_type=EdgeType.CONTAINS,
                project_id=project_id,
            )
        )

        # INHERITS edges
        for base in bases:
            if base and base not in ("object",):
                base_id = self._make_id(project_id, "cls", base)
                edges.append(
                    Edge(
                        source_id=cls_id,
                        target_id=base_id,
                        edge_type=EdgeType.INHERITS,
                        project_id=project_id,
                    )
                )

        # Extract methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_node, fn_edges = self._extract_function(
                    item,
                    file_path,
                    cls_id,
                    project_id,
                    qualified,
                    is_test,
                )
                nodes.append(fn_node)
                edges.extend(fn_edges)

        return nodes, edges

    # ------------------------------------------------------------------
    # Function extraction
    # ------------------------------------------------------------------

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        parent_id: str,
        project_id: str,
        parent_name: str,
        is_test: bool,
    ) -> tuple[list[Node], list[Edge]]:
        """Extract a function or method definition."""
        qualified = f"{parent_name}.{node.name}" if parent_name else node.name
        fn_id = self._make_id(project_id, "fn", qualified)
        docstring = ast.get_docstring(node) or ""

        decorators = [self._name_from_expr(d) for d in node.decorator_list]
        args = self._extract_args(node.args)
        return_annotation = self._name_from_expr(node.returns) if node.returns else ""

        is_test_fn = is_test and (node.name.startswith("test_") or node.name.startswith("test"))
        ntype = NodeType.TEST if is_test_fn else NodeType.FUNCTION

        fn_node = Node(
            id=fn_id,
            node_type=ntype,
            name=node.name,
            qualified_name=qualified,
            file_path=file_path,
            language="python",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            content=docstring[:1000],
            metadata={
                "args": args,
                "return_type": return_annotation,
                "decorators": decorators,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "is_property": "property" in decorators,
                "is_staticmethod": "staticmethod" in decorators,
                "is_classmethod": "classmethod" in decorators,
            },
            project_id=project_id,
        )

        edges = [
            Edge(
                source_id=parent_id,
                target_id=fn_id,
                edge_type=EdgeType.CONTAINS,
                project_id=project_id,
            )
        ]

        return fn_node, edges

    # ------------------------------------------------------------------
    # Import extraction
    # ------------------------------------------------------------------

    def _extract_import(
        self,
        node: ast.Import | ast.ImportFrom,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> tuple[list[Node], list[Edge]]:
        """Extract import statements as IMPORT nodes."""
        nodes: list[Node] = []
        edges: list[Edge] = []

        if isinstance(node, ast.Import):
            for alias in node.names:
                imp_name = alias.name
                imp_id = self._make_id(project_id, "imp", f"{file_path}:{imp_name}")
                nodes.append(
                    Node(
                        id=imp_id,
                        node_type=NodeType.IMPORT,
                        name=imp_name,
                        qualified_name=imp_name,
                        file_path=file_path,
                        language="python",
                        line_start=node.lineno,
                        content=f"import {imp_name}",
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
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names or []:
                imp_name = f"{module}.{alias.name}" if module else alias.name
                imp_id = self._make_id(project_id, "imp", f"{file_path}:{imp_name}")
                level_dots = "." * (node.level or 1)
                if module:
                    content = f"from {module} import {alias.name}"
                else:
                    content = f"from {level_dots} import {alias.name}"
                nodes.append(
                    Node(
                        id=imp_id,
                        node_type=NodeType.IMPORT,
                        name=alias.name,
                        qualified_name=imp_name,
                        file_path=file_path,
                        language="python",
                        line_start=node.lineno,
                        content=content,
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

        return nodes, edges

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_id(project_id: str, prefix: str, name: str) -> str:
        """Deterministic node ID."""
        raw = f"{project_id}:{prefix}:{name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _name_from_expr(node: ast.expr | None) -> str:
        """Best-effort name extraction from an AST expression."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Call):
            return PythonAnalyzer._name_from_expr(node.func)
        return ""

    @staticmethod
    def _extract_args(args: ast.arguments) -> list[str]:
        """Extract argument names from function signature."""
        result = []
        for arg in args.args:
            name = arg.arg
            if arg.annotation:
                ann = PythonAnalyzer._name_from_expr(arg.annotation)
                if ann:
                    name = f"{name}: {ann}"
            result.append(name)
        return result

    @staticmethod
    def _path_to_module(file_path: str) -> str:
        """Convert ``foo/bar/baz.py`` to ``foo.bar.baz``."""
        base = file_path.replace(os.sep, "/")
        if base.endswith("/__init__.py"):
            base = base[:-12]
        elif base.endswith(".py"):
            base = base[:-3]
        return base.replace("/", ".")

    @staticmethod
    def _is_test_file(file_path: str) -> bool:
        """Heuristic: is this a test file?"""
        basename = os.path.basename(file_path)
        return (
            basename.startswith("test_")
            or basename.endswith("_test.py")
            or "/tests/" in file_path
            or "/test/" in file_path
            or file_path.startswith("tests/")
        )

    @staticmethod
    def _is_top_level(tree: ast.Module, node: ast.AST) -> bool:
        """Check if a node is at module top-level (not nested in a class)."""
        for top in tree.body:
            if top is node:
                return True
        return False

    # ------------------------------------------------------------------
    # Call graph extraction
    # ------------------------------------------------------------------

    _BUILTIN_NAMES = frozenset(
        {
            "super",
            "print",
            "len",
            "range",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "bool",
            "type",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
        }
    )

    def _extract_call_graph(
        self,
        tree: ast.Module,
        file_path: str,
        file_node_id: str,
        project_id: str,
        module_name: str,
        defined_names: set[str],
    ) -> list[Edge]:
        """Extract function-to-function CALLS edges from the AST."""
        edges: list[Edge] = []
        seen_calls: set[tuple] = set()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            caller_qname = self._resolve_caller(tree, node, module_name)
            if not caller_qname:
                continue

            caller_id = self._make_id(project_id, "fn", caller_qname)
            caller_parent = self._find_parent_class(tree, node)

            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue

                callee_name = self._name_from_expr(child.func)
                if not callee_name or callee_name in self._BUILTIN_NAMES:
                    continue

                callee_qname = self._resolve_callee(
                    callee_name,
                    module_name,
                    caller_parent,
                    defined_names,
                )
                if not callee_qname:
                    continue

                callee_id = self._make_id(project_id, "fn", callee_qname)
                pair = (caller_id, callee_id)
                if pair in seen_calls:
                    continue
                seen_calls.add(pair)

                edges.append(
                    Edge(
                        source_id=caller_id,
                        target_id=callee_id,
                        edge_type=EdgeType.CALLS,
                        confidence=0.8,
                        provenance="INFERRED",
                        metadata={"caller": caller_qname, "callee": callee_qname},
                        project_id=project_id,
                    )
                )

        return edges

    def _resolve_caller(
        self,
        tree: ast.Module,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        module_name: str,
    ) -> str:
        """Resolve a function node to its fully-qualified caller name."""
        parent = self._find_parent_class(tree, node)
        if parent:
            return f"{module_name}.{parent}.{node.name}"
        if self._is_top_level(tree, node):
            return f"{module_name}.{node.name}"
        return ""

    @staticmethod
    def _resolve_callee(
        callee_name: str,
        module_name: str,
        caller_parent: str,
        defined_names: set[str],
    ) -> str:
        """Resolve callee name to qualified name. Returns '' if unresolvable."""
        if callee_name in defined_names:
            return f"{module_name}.{callee_name}"
        if "." in callee_name:
            parts = callee_name.split(".")
            if parts[0] == "self" and caller_parent:
                return f"{module_name}.{caller_parent}.{'.'.join(parts[1:])}"
            return callee_name
        return ""

    @staticmethod
    def _find_parent_class(tree: ast.Module, target_func: ast.AST) -> str:
        """Find the enclosing ClassDef name for a function, if any."""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item is target_func:
                        return node.name
        return ""

    # ------------------------------------------------------------------
    # Rationale comment extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rationale(
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
        *,
        max_per_file: int = 500,
    ) -> tuple[list[Node], list[Edge]]:
        """Extract WHY/TODO/HACK/NOTE/FIXME comments as RATIONALE nodes."""
        nodes: list[Node] = []
        edges: list[Edge] = []

        for i, match in enumerate(_RATIONALE_RE.finditer(source)):
            if i >= max_per_file:
                logger.warning(
                    "Rationale limit (%d) reached for %s; skipping remaining",
                    max_per_file,
                    file_path,
                )
                break
            tag = match.group(1).upper()
            text = match.group(2).strip()
            line = source[: match.start()].count("\n") + 1
            r_id = hashlib.sha256(
                f"{project_id}:rationale:{file_path}:{line}:{tag}".encode(),
            ).hexdigest()[:16]

            nodes.append(
                Node(
                    id=r_id,
                    node_type=NodeType.RATIONALE,
                    name=f"{tag}: {text[:80]}",
                    qualified_name=f"{file_path}:{line}",
                    file_path=file_path,
                    language="python",
                    line_start=line,
                    content=text,
                    metadata={"tag": tag, "full_text": text},
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=r_id,
                    edge_type=EdgeType.DOCUMENTS,
                    confidence=1.0,
                    provenance="EXTRACTED",
                    project_id=project_id,
                )
            )

        return nodes, edges
