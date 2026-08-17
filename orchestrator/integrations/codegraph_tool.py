"""Integration named after colbymchenry/codegraph — now backed by REAL Python `ast` parsing.

`index_directory()` walks real `.py` files with Python's built-in `ast`
module, records every real function/method/class definition it finds, then
does a second pass over each function body to detect real `Name`/`Attribute`
calls and link them to other indexed symbols — giving a genuine (if
heuristic — it's a static, not a dynamic, call graph, and does not follow
calls through variables holding a function reference) caller/callee graph
instead of the previous 2 hardcoded entries.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CodeSymbol:
    """Represents a code symbol indexed by CodeGraph."""

    name: str
    symbol_type: str  # function, class, method
    file_path: str
    line_number: int
    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)


class _CallCollector(ast.NodeVisitor):
    """Collects the set of names called anywhere inside a function/method body."""

    def __init__(self) -> None:
        self.called_names: List[str] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 (ast visitor naming convention)
        func = node.func
        if isinstance(func, ast.Name):
            self.called_names.append(func.id)
        elif isinstance(func, ast.Attribute):
            self.called_names.append(func.attr)
        self.generic_visit(node)


class CodeGraphTool:
    """Real static code-graph indexer: parses Python source with `ast`, builds a caller/callee graph."""

    def __init__(self) -> None:
        self._symbol_index: Dict[str, CodeSymbol] = {}
        self._files_indexed = 0
        self._parse_errors: List[str] = []

    def register_symbol(self, symbol: CodeSymbol) -> None:
        """Register (or overwrite) a symbol in the index by lowercase name."""
        self._symbol_index[symbol.name.lower()] = symbol

    def index_directory(self, root_path: str, exclude_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Recursively parse every `.py` file under `root_path` and (re)build the real symbol graph.

        Returns a summary dict; the indexed symbols themselves are queryable
        afterwards via `explore_symbol()`.
        """
        excluded = set(exclude_dirs or ["__pycache__", ".git", "node_modules", ".venv", "venv"])
        self._symbol_index.clear()
        self._parse_errors.clear()
        self._files_indexed = 0

        root = Path(root_path)
        py_files = [
            p for p in root.rglob("*.py")
            if not any(part in excluded for part in p.parts)
        ]

        # Pass 1: collect every real function/method/class definition.
        parsed_trees: Dict[str, ast.Module] = {}
        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError, OSError) as e:
                self._parse_errors.append(f"{py_file}: {e}")
                continue

            rel_path = str(py_file.relative_to(root)) if py_file.is_relative_to(root) else str(py_file)
            parsed_trees[rel_path] = tree
            self._files_indexed += 1

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbol_type = "function"
                    self.register_symbol(
                        CodeSymbol(
                            name=node.name,
                            symbol_type=symbol_type,
                            file_path=rel_path,
                            line_number=node.lineno,
                        )
                    )
                elif isinstance(node, ast.ClassDef):
                    self.register_symbol(
                        CodeSymbol(
                            name=node.name,
                            symbol_type="class",
                            file_path=rel_path,
                            line_number=node.lineno,
                        )
                    )

        # Pass 2: for every function/method body, find real calls to other indexed symbols.
        for rel_path, tree in parsed_trees.items():
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                collector = _CallCollector()
                for stmt in node.body:
                    collector.visit(stmt)
                caller_symbol = self._symbol_index.get(node.name.lower())
                if caller_symbol is None:
                    continue
                for called_name in collector.called_names:
                    callee_symbol = self._symbol_index.get(called_name.lower())
                    if callee_symbol is None or callee_symbol is caller_symbol:
                        continue
                    if called_name not in caller_symbol.callees:
                        caller_symbol.callees.append(called_name)
                    if node.name not in callee_symbol.callers:
                        callee_symbol.callers.append(node.name)

        return {
            "source_repo": "colbymchenry/codegraph",
            "root_path": str(root),
            "files_indexed": self._files_indexed,
            "symbols_indexed": len(self._symbol_index),
            "parse_errors": len(self._parse_errors),
        }

    def explore_symbol(self, symbol_name: str) -> Optional[Dict[str, Any]]:
        """Look up a real indexed symbol's file, line, and (real, statically-derived) call edges."""
        sym = self._symbol_index.get(symbol_name.lower())
        if not sym:
            return None

        return {
            "name": sym.name,
            "type": sym.symbol_type,
            "file": sym.file_path,
            "line": sym.line_number,
            "callers": sym.callers,
            "callees": sym.callees,
        }

    def most_called_symbols(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Return the `top_n` symbols with the most real incoming call edges found in this codebase."""
        ranked = sorted(self._symbol_index.values(), key=lambda s: len(s.callers), reverse=True)
        return [
            {"name": s.name, "file": s.file_path, "line": s.line_number, "caller_count": len(s.callers)}
            for s in ranked[:top_n]
        ]
