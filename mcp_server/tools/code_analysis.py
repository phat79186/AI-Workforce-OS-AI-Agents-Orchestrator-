"""Code analysis MCP tools for static analysis and code quality."""

import ast
import json
import logging
import re
from typing import Any, Dict, List

from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)


async def analyze_python_complexity(ctx: Context, file_path: str) -> Dict[str, Any]:
    """Analyze Python code complexity metrics.

    Args:
        ctx: MCP context
        file_path: Path to Python file to analyze

    Returns:
        Complexity metrics including cyclomatic complexity, lines of code,
        function count, and class count.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports = 0
        total_complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                complexity = _calculate_complexity(node)
                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": complexity,
                        "args": len(node.args.args),
                    }
                )
                total_complexity += complexity
            elif isinstance(node, ast.ClassDef):
                methods = [
                    n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes.append({"name": node.name, "line": node.lineno, "methods": len(methods)})
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1

        metrics: Dict[str, Any] = {
            "file": file_path,
            "lines_of_code": len(source.splitlines()),
            "blank_lines": sum(1 for line in source.splitlines() if not line.strip()),
            "comment_lines": sum(1 for line in source.splitlines() if line.strip().startswith("#")),
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "total_complexity": total_complexity,
        }

        # Summary
        metrics["summary"] = {
            "function_count": len(functions),
            "class_count": len(classes),
            "avg_complexity": total_complexity / max(len(functions), 1),
            "high_complexity_functions": [f["name"] for f in functions if f["complexity"] > 10],
        }

        return metrics

    except Exception as e:
        return {"error": str(e), "file": file_path}


def _calculate_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity of a function."""
    complexity = 1  # Base complexity

    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, (ast.comprehension,)):
            complexity += 1
        elif isinstance(child, ast.IfExp):
            complexity += 1

    return complexity


async def find_code_patterns(
    ctx: Context, directory: str, pattern_type: str = "all"
) -> Dict[str, Any]:
    """Find common code patterns and anti-patterns.

    Args:
        ctx: MCP context
        directory: Directory to search
        pattern_type: Type of patterns to find (security, performance, style, all)

    Returns:
        Dictionary of found patterns with file locations.
    """
    patterns: Dict[str, List[tuple]] = {
        "security": [
            (r"subprocess\..*shell\s*=\s*True", "Shell injection risk"),
            (r"eval\s*\(", "Eval usage - potential code injection"),
            (r"exec\s*\(", "Exec usage - potential code injection"),
            (r"\.format\s*\([^)]*user|input", "String formatting with user input"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
        ],
        "performance": [
            (r"for\s+\w+\s+in\s+.*\.keys\(\)", "Unnecessary .keys() call"),
            (r"\+\s*=\s*.*\+", "String concatenation in loop"),
            (r"time\.sleep\s*\(\s*0\s*\)", "Sleep(0) - use yield instead"),
        ],
        "style": [
            (r"except\s*:", "Bare except clause"),
            (r"# TODO", "TODO comment"),
            (r"# FIXME", "FIXME comment"),
            (r"print\s*\(", "Print statement (use logging)"),
        ],
    }

    if pattern_type != "all":
        patterns = {pattern_type: patterns.get(pattern_type, [])}

    found_patterns: List[Dict[str, Any]] = []
    summary: Dict[str, int] = {}

    import glob

    py_files = glob.glob(f"{directory}/**/*.py", recursive=True)

    for file_path in py_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            for category, pattern_list in patterns.items():
                for pattern, description in pattern_list:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            found_patterns.append(
                                {
                                    "file": file_path,
                                    "line": i,
                                    "category": category,
                                    "pattern": description,
                                    "content": line.strip()[:100],
                                }
                            )
        except Exception as e:  # noqa: B112
            # Skip files that cannot be parsed, log and continue
            logger.warning("Could not parse %s: %s", file_path, e)
            continue

    # Summary by category
    for category in patterns.keys():
        count = sum(1 for p in found_patterns if p["category"] == category)
        summary[category] = count

    return {"patterns": found_patterns, "summary": summary}


async def analyze_dependencies(
    ctx: Context, requirements_file: str = "requirements.txt"
) -> Dict[str, Any]:
    """Analyze project dependencies for issues.

    Args:
        ctx: MCP context
        requirements_file: Path to requirements file

    Returns:
        Analysis of dependencies including unpinned versions and potential issues.
    """
    dependencies: List[Dict[str, Any]] = []
    issues: List[Dict[str, str]] = []

    try:
        with open(requirements_file, encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse dependency
            dep: Dict[str, Any] = {"raw": line, "name": "", "version": "", "pinned": False}

            if "==" in line:
                parts = line.split("==")
                dep["name"] = parts[0].strip()
                dep["version"] = parts[1].strip() if len(parts) > 1 else ""
                dep["pinned"] = True
            elif ">=" in line:
                parts = line.split(">=")
                dep["name"] = parts[0].strip()
                dep["version"] = f">={parts[1].strip()}" if len(parts) > 1 else ""
                dep["pinned"] = False
                issues.append(
                    {
                        "type": "unpinned",
                        "dependency": dep["name"],
                        "message": "Version not pinned - may cause reproducibility issues",
                    }
                )
            else:
                dep["name"] = line.split("[")[0].strip()
                dep["pinned"] = False
                issues.append(
                    {
                        "type": "unpinned",
                        "dependency": dep["name"],
                        "message": "No version specified",
                    }
                )

            dependencies.append(dep)

        summary = {
            "total": len(dependencies),
            "pinned": sum(1 for d in dependencies if d["pinned"]),
            "unpinned": sum(1 for d in dependencies if not d["pinned"]),
            "issues_count": len(issues),
        }

        return {"dependencies": dependencies, "issues": issues, "summary": summary}

    except FileNotFoundError:
        return {"error": f"File not found: {requirements_file}"}
    except Exception as e:
        return {"error": str(e)}


async def generate_code_summary(ctx: Context, file_path: str) -> Dict[str, Any]:
    """Generate a summary of a code file.

    Args:
        ctx: MCP context
        file_path: Path to file to summarize

    Returns:
        Summary including structure, exports, and documentation status.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        exports: List[str] = []
        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []

        documented = 0
        total = 0

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                total += 1
                has_doc = ast.get_docstring(node) is not None
                if has_doc:
                    documented += 1

                functions.append(
                    {
                        "name": node.name,
                        "async": isinstance(node, ast.AsyncFunctionDef),
                        "documented": has_doc,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [_get_decorator_name(d) for d in node.decorator_list],
                    }
                )

                if not node.name.startswith("_"):
                    exports.append(node.name)

            elif isinstance(node, ast.ClassDef):
                total += 1
                has_doc = ast.get_docstring(node) is not None
                if has_doc:
                    documented += 1

                methods: List[str] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(item.name)

                classes.append(
                    {
                        "name": node.name,
                        "documented": has_doc,
                        "methods": methods,
                        "bases": [_get_name(b) for b in node.bases],
                    }
                )

                if not node.name.startswith("_"):
                    exports.append(node.name)

        doc_coverage = (documented / total * 100) if total > 0 else 100.0

        return {
            "file": file_path,
            "module_docstring": ast.get_docstring(tree),
            "exports": exports,
            "functions": functions,
            "classes": classes,
            "documentation_coverage": doc_coverage,
        }

    except Exception as e:
        return {"error": str(e), "file": file_path}


def _get_decorator_name(node: ast.AST) -> str:
    """Extract decorator name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        return _get_decorator_name(node.func)
    return "unknown"


def _get_name(node: ast.AST) -> str:
    """Extract name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    return "unknown"


# Tool registration for FastMCP
def register_code_analysis_tools(mcp):
    """Register code analysis tools with FastMCP server."""

    @mcp.tool()
    async def code_complexity(file_path: str) -> str:
        """Analyze Python code complexity metrics.

        Args:
            file_path: Path to Python file to analyze
        """
        result = await analyze_python_complexity(None, file_path)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def find_patterns(directory: str, pattern_type: str = "all") -> str:
        """Find code patterns and anti-patterns.

        Args:
            directory: Directory to search
            pattern_type: Type of patterns (security, performance, style, all)
        """
        result = await find_code_patterns(None, directory, pattern_type)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def analyze_deps(requirements_file: str = "requirements.txt") -> str:
        """Analyze project dependencies.

        Args:
            requirements_file: Path to requirements file
        """
        result = await analyze_dependencies(None, requirements_file)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def code_summary(file_path: str) -> str:
        """Generate summary of a code file.

        Args:
            file_path: Path to file to summarize
        """
        result = await generate_code_summary(None, file_path)
        return json.dumps(result, indent=2)
