"""Testing utility MCP tools for test generation and analysis."""

import ast
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context


async def generate_test_cases(
    ctx: Context, file_path: str, framework: str = "pytest"
) -> Dict[str, Any]:
    """Generate test case suggestions for a Python file.

    Args:
        ctx: MCP context
        file_path: Path to Python file
        framework: Test framework (pytest or unittest)

    Returns:
        Suggested test cases with code templates.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        test_cases: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                if func_name.startswith("_"):
                    continue

                # Analyze function signature
                args = [arg.arg for arg in node.args.args if arg.arg != "self"]
                has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))

                cases: List[Dict[str, str]] = []

                # Basic functionality test
                cases.append(
                    {
                        "name": f"test_{func_name}_basic",
                        "description": "Test basic functionality",
                        "template": _generate_test_template(func_name, args, framework, "basic"),
                    }
                )

                # Edge cases
                if args:
                    cases.append(
                        {
                            "name": f"test_{func_name}_edge_cases",
                            "description": "Test edge cases and boundary conditions",
                            "template": _generate_test_template(func_name, args, framework, "edge"),
                        }
                    )

                # Error handling
                cases.append(
                    {
                        "name": f"test_{func_name}_error_handling",
                        "description": "Test error handling",
                        "template": _generate_test_template(func_name, args, framework, "error"),
                    }
                )

                # Return value test if function returns
                if has_return:
                    cases.append(
                        {
                            "name": f"test_{func_name}_return_value",
                            "description": "Test return value",
                            "template": _generate_test_template(
                                func_name, args, framework, "return"
                            ),
                        }
                    )

                test_cases.append(
                    {
                        "function": func_name,
                        "args": args,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "suggested_tests": cases,
                    }
                )

            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                if class_name.startswith("_"):
                    continue

                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]

                class_cases: List[Dict[str, str]] = [
                    {
                        "name": f"test_{class_name}_instantiation",
                        "description": "Test class instantiation",
                        "template": _generate_class_test_template(class_name, framework, "init"),
                    }
                ]

                for method in methods:
                    class_cases.append(
                        {
                            "name": f"test_{class_name}_{method}",
                            "description": f"Test {method} method",
                            "template": _generate_class_test_template(
                                class_name, framework, "method", method
                            ),
                        }
                    )

                test_cases.append(
                    {
                        "class": class_name,
                        "methods": methods,
                        "suggested_tests": class_cases,
                    }
                )

        return {
            "file": file_path,
            "framework": framework,
            "test_cases": test_cases,
            "total_tests_suggested": sum(len(tc.get("suggested_tests", [])) for tc in test_cases),
        }

    except Exception as e:
        return {"error": str(e), "file": file_path}


def _generate_test_template(func_name: str, args: List[str], framework: str, test_type: str) -> str:
    """Generate test code template."""
    if framework == "pytest":
        if test_type == "basic":
            args_str = ", ".join([f"{arg}=..." for arg in args]) if args else ""
            return f"""def test_{func_name}_basic():
    # Arrange
    {chr(10).join([f'    {arg} = ...' for arg in args]) if args else '    pass'}

    # Act
    result = {func_name}({args_str})

    # Assert
    assert result is not None
"""
        elif test_type == "edge":
            return f"""def test_{func_name}_edge_cases():
    # Test with empty/None values
    # Test with boundary values
    # Test with special characters
    pass
"""
        elif test_type == "error":
            return f"""def test_{func_name}_raises_on_invalid_input():
    with pytest.raises(ValueError):
        {func_name}(invalid_input)
"""
        else:
            return f"""def test_{func_name}_returns_expected_type():
    result = {func_name}(...)
    assert isinstance(result, expected_type)
"""
    else:  # unittest
        return f"""def test_{func_name}(self):
    self.assertEqual({func_name}(...), expected)
"""


def _generate_class_test_template(
    class_name: str, framework: str, test_type: str, method: Optional[str] = None
) -> str:
    """Generate class test code template."""
    if framework == "pytest":
        if test_type == "init":
            return f"""def test_{class_name}_instantiation():
    instance = {class_name}()
    assert instance is not None
"""
        else:
            return f"""def test_{class_name}_{method}():
    instance = {class_name}()
    result = instance.{method}()
    assert result is not None
"""
    return ""


async def generate_mock_stubs(ctx: Context, file_path: str) -> Dict[str, Any]:
    """Generate mock stubs for dependencies in a Python file.

    Args:
        ctx: MCP context
        file_path: Path to Python file

    Returns:
        Mock stubs for external dependencies.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        imports: List[str] = []
        external_calls: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    external_calls.append(
                        {
                            "call": (
                                ast.unparse(node.func)
                                if hasattr(ast, "unparse")
                                else str(node.func)
                            ),
                            "line": node.lineno,
                        }
                    )

        # Generate mock suggestions
        mock_suggestions: List[Dict[str, Any]] = []
        for imp in imports:
            if not imp.startswith("_") and imp not in ["typing", "os", "sys", "re", "json"]:
                mock_suggestions.append(
                    {
                        "module": imp,
                        "mock_code": f'@patch("{imp}")\ndef test_with_mocked_{imp.replace(".", "_")}(mock_{imp.split(".")[-1]}):\n    mock_{imp.split(".")[-1]}.return_value = ...\n',
                        "fixture_code": f'@pytest.fixture\ndef mock_{imp.split(".")[-1]}():\n    with patch("{imp}") as mock:\n        yield mock\n',
                    }
                )

        return {
            "file": file_path,
            "imports": imports,
            "external_calls": external_calls[:20],  # Limit
            "mock_suggestions": mock_suggestions,
        }

    except Exception as e:
        return {"error": str(e), "file": file_path}


async def analyze_test_coverage(ctx: Context, coverage_file: str) -> Dict[str, Any]:
    """Analyze test coverage from coverage.json or coverage.xml.

    Args:
        ctx: MCP context
        coverage_file: Path to coverage file

    Returns:
        Coverage analysis with recommendations.
    """
    try:
        if coverage_file.endswith(".json"):
            with open(coverage_file, encoding="utf-8") as f:
                data = json.load(f)

            files_coverage: List[Dict[str, Any]] = []
            for file_path, file_data in data.get("files", {}).items():
                summary = file_data.get("summary", {})
                files_coverage.append(
                    {
                        "file": file_path,
                        "covered_lines": summary.get("covered_lines", 0),
                        "missing_lines": summary.get("missing_lines", 0),
                        "coverage_percent": summary.get("percent_covered", 0),
                    }
                )

            total = data.get("totals", {})
            return {
                "total_coverage": total.get("percent_covered", 0),
                "files": files_coverage,
                "low_coverage_files": [f for f in files_coverage if f["coverage_percent"] < 80],
                "recommendations": _generate_coverage_recommendations(files_coverage),
            }

        elif coverage_file.endswith(".xml"):
            import xml.etree.ElementTree as ET  # noqa: B405

            tree = ET.parse(coverage_file)  # noqa: B314  # trusted local file
            root = tree.getroot()

            packages = root.findall(".//package")
            xml_files_coverage: List[Dict[str, Any]] = []

            for package in packages:
                for cls in package.findall(".//class"):
                    filename = cls.get("filename", "")
                    line_rate = float(cls.get("line-rate", 0)) * 100
                    xml_files_coverage.append({"file": filename, "coverage_percent": line_rate})

            total_rate = float(root.get("line-rate", 0)) * 100
            return {
                "total_coverage": total_rate,
                "files": xml_files_coverage,
                "low_coverage_files": [f for f in xml_files_coverage if f["coverage_percent"] < 80],
                "recommendations": _generate_coverage_recommendations(xml_files_coverage),
            }

        return {"error": "Unsupported coverage file format"}

    except Exception as e:
        return {"error": str(e)}


def _generate_coverage_recommendations(files: List[Dict[str, Any]]) -> List[str]:
    """Generate coverage improvement recommendations."""
    recommendations: List[str] = []

    low_coverage = [f for f in files if f.get("coverage_percent", 0) < 50]
    if low_coverage:
        recommendations.append(
            f"Focus on improving coverage for {len(low_coverage)} files below 50%"
        )

    medium_coverage = [f for f in files if 50 <= f.get("coverage_percent", 0) < 80]
    if medium_coverage:
        recommendations.append(
            f"Consider adding tests for {len(medium_coverage)} files between 50-80%"
        )

    if not recommendations:
        recommendations.append("Coverage is good! Consider adding edge case tests.")

    return recommendations


async def parse_test_results(
    ctx: Context, results_file: str, format: str = "pytest"
) -> Dict[str, Any]:
    """Parse test results from various formats.

    Args:
        ctx: MCP context
        results_file: Path to test results file
        format: Format of results (pytest, junit, json)

    Returns:
        Parsed test results with statistics.
    """
    try:
        if format == "json" or results_file.endswith(".json"):
            with open(results_file, encoding="utf-8") as f:
                data = json.load(f)
            return {
                "format": "json",
                "summary": data.get("summary", {}),
                "tests": data.get("tests", [])[:50],  # Limit
            }

        elif format == "junit" or results_file.endswith(".xml"):
            import xml.etree.ElementTree as ET  # noqa: B405

            tree = ET.parse(results_file)  # noqa: B314  # trusted local file
            root = tree.getroot()

            tests: List[Dict[str, Any]] = []
            for testcase in root.findall(".//testcase"):
                test: Dict[str, Any] = {
                    "name": testcase.get("name", ""),
                    "classname": testcase.get("classname", ""),
                    "time": float(testcase.get("time", 0)),
                    "status": "passed",
                }

                if testcase.find("failure") is not None:
                    test["status"] = "failed"
                    failure = testcase.find("failure")
                    test["failure_message"] = (
                        failure.get("message", "") if failure is not None else ""
                    )
                elif testcase.find("error") is not None:
                    test["status"] = "error"
                elif testcase.find("skipped") is not None:
                    test["status"] = "skipped"

                tests.append(test)

            testsuite = root if root.tag == "testsuite" else root.find("testsuite")
            return {
                "format": "junit",
                "summary": {
                    "tests": int(testsuite.get("tests", 0)) if testsuite is not None else 0,
                    "failures": int(testsuite.get("failures", 0)) if testsuite is not None else 0,
                    "errors": int(testsuite.get("errors", 0)) if testsuite is not None else 0,
                    "skipped": int(testsuite.get("skipped", 0)) if testsuite is not None else 0,
                    "time": float(testsuite.get("time", 0)) if testsuite is not None else 0,
                },
                "tests": tests[:50],
                "failed_tests": [t for t in tests if t["status"] == "failed"],
            }

        return {"error": f"Unsupported format: {format}"}

    except Exception as e:
        return {"error": str(e)}


def register_testing_tools(mcp: Any) -> None:
    """Register testing tools with MCP server."""
    mcp.tool()(generate_test_cases)
    mcp.tool()(generate_mock_stubs)
    mcp.tool()(analyze_test_coverage)
    mcp.tool()(parse_test_results)


# Alias for backward compatibility
generate_test_stub = generate_mock_stubs
