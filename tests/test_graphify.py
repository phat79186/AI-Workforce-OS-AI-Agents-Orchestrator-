"""
Comprehensive tests for the Graphify system.

Covers: schema, config, graph store, scanner, all analyzers,
FTS search, query engine, export formatters, and CLI.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from graphify.core.config import GraphifyConfig
from graphify.core.graph import GraphStore
from graphify.core.scanner import Scanner
from graphify.core.schema import (
    Edge,
    EdgeType,
    Language,
    Node,
    NodeType,
    ProjectSummary,
    classify_language,
    generate_project_id,
)
from graphify.export.formatters import GraphExporter
from graphify.search.fts_engine import FTSEngine
from graphify.search.query_engine import QueryEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    """In-memory graph store."""
    s = GraphStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal multi-language sample project."""
    # Python files
    (tmp_path / "app.py").write_text(
        '"""Main app."""\n\nimport os\nimport json\n\n\n'
        "class App:\n"
        '    """Application class."""\n\n'
        "    def __init__(self):\n"
        "        self.name = 'test'\n\n"
        "    def run(self):\n"
        '        """Run the app."""\n'
        "        return True\n\n\n"
        "def main():\n"
        '    """Entry point."""\n'
        "    app = App()\n"
        "    app.run()\n",
        encoding="utf-8",
    )

    (tmp_path / "utils.py").write_text(
        "from app import App\n\n\n"
        "def helper(x: int) -> str:\n"
        '    """Helper function."""\n'
        "    return str(x)\n\n\n"
        "class BaseHelper:\n"
        '    """Base helper."""\n'
        "    pass\n\n\n"
        "class AdvancedHelper(BaseHelper):\n"
        '    """Advanced helper inherits BaseHelper."""\n'
        "    pass\n",
        encoding="utf-8",
    )

    # Test file
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        "from app import App\n\n\n"
        "class TestApp:\n"
        "    def test_init(self):\n"
        "        app = App()\n"
        "        assert app.name == 'test'\n\n"
        "    def test_run(self):\n"
        "        app = App()\n"
        "        assert app.run() is True\n",
        encoding="utf-8",
    )

    # JS file
    (tmp_path / "index.js").write_text(
        "import React from 'react';\n"
        "import { useState } from 'react';\n\n"
        "export class Widget extends React.Component {\n"
        "  render() { return null; }\n"
        "}\n\n"
        "export function createApp() {\n"
        "  return new Widget();\n"
        "}\n\n"
        "const helper = () => {};\n",
        encoding="utf-8",
    )

    # Config files
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "test-project",
                "dependencies": {"react": "^18.0.0", "express": "^4.18.0"},
                "devDependencies": {"jest": "^29.0.0"},
                "scripts": {"start": "node index.js", "test": "jest"},
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "requirements.txt").write_text("flask>=2.0\npytest>=7.0\n", encoding="utf-8")

    # Markdown doc
    (tmp_path / "README.md").write_text(
        "# Test Project\n\n"
        "## Installation\n\n"
        "Run `pip install`.\n\n"
        "## Usage\n\n"
        "```python\nfrom app import App\n```\n\n"
        "## API\n\n"
        "See docs.\n",
        encoding="utf-8",
    )

    # YAML config
    (tmp_path / "config.yaml").write_text(
        "database:\n  host: localhost\n  port: 5432\nlogging:\n  level: INFO\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def scanned_store(sample_project):
    """Return a store already scanned from sample_project."""
    store = GraphStore(":memory:")
    config = GraphifyConfig()
    scanner = Scanner(str(sample_project), store, config)
    scanner.scan()
    yield store, generate_project_id(str(sample_project))
    store.close()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchema:
    """Tests for schema models and helpers."""

    def test_generate_project_id_deterministic(self, tmp_path):
        pid1 = generate_project_id(str(tmp_path))
        pid2 = generate_project_id(str(tmp_path))
        assert pid1 == pid2
        assert len(pid1) == 16

    def test_generate_project_id_different_paths(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        assert generate_project_id(str(tmp_path / "a")) != generate_project_id(str(tmp_path / "b"))

    def test_classify_language_python(self):
        assert classify_language("foo/bar.py") == Language.PYTHON

    def test_classify_language_js(self):
        assert classify_language("src/index.js") == Language.JAVASCRIPT

    def test_classify_language_ts(self):
        assert classify_language("src/app.tsx") == Language.TYPESCRIPT

    def test_classify_language_unknown(self):
        assert classify_language("file.xyz") == Language.UNKNOWN

    def test_classify_language_dockerfile(self):
        assert classify_language("Dockerfile") == Language.DOCKERFILE

    def test_classify_language_yaml(self):
        assert classify_language("config.yml") == Language.YAML

    def test_node_searchable_text(self):
        node = Node(name="TestClass", content="A test class", metadata={"desc": "hello"})
        text = node.searchable_text
        assert "TestClass" in text
        assert "hello" in text

    def test_node_types_enum(self):
        assert NodeType.PROJECT.value == "PROJECT"
        assert NodeType.FUNCTION.value == "FUNCTION"
        assert len(NodeType) >= 10

    def test_edge_types_enum(self):
        assert EdgeType.CONTAINS.value == "CONTAINS"
        assert EdgeType.IMPORTS.value == "IMPORTS"


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfig:
    """Tests for GraphifyConfig."""

    def test_defaults(self):
        config = GraphifyConfig()
        assert config.max_files == 10_000
        assert config.max_depth == 30
        assert config.worker_threads == 4
        assert ".git" in config.skip_dirs

    def test_resolve_db_path_default(self, tmp_path):
        config = GraphifyConfig()
        path = config.resolve_db_path(str(tmp_path))
        assert path.endswith(".graphify.db")
        assert str(tmp_path) in path

    def test_resolve_db_path_custom(self, tmp_path):
        config = GraphifyConfig(db_path="/custom/path.db")
        assert config.resolve_db_path(str(tmp_path)) == "/custom/path.db"

    def test_frozen(self):
        config = GraphifyConfig()
        with pytest.raises(AttributeError):
            config.max_files = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GraphStore tests
# ---------------------------------------------------------------------------


class TestGraphStore:
    """Tests for the SQLite graph store."""

    def test_add_and_get_node(self, store):
        node = Node(id="n1", node_type=NodeType.FILE, name="test.py", project_id="p1")
        store.add_node(node)
        retrieved = store.get_node("n1")
        assert retrieved is not None
        assert retrieved.name == "test.py"
        assert retrieved.node_type == NodeType.FILE

    def test_add_node_upsert(self, store):
        store.add_node(Node(id="n1", name="old", project_id="p1"))
        store.add_node(Node(id="n1", name="new", project_id="p1"))
        assert store.get_node("n1").name == "new"

    def test_bulk_insert(self, store):
        nodes = [Node(id=f"n{i}", name=f"node{i}", project_id="p1") for i in range(100)]
        count = store.add_nodes_bulk(nodes)
        assert count == 100
        assert len(store.get_nodes(project_id="p1", limit=200)) == 100

    def test_delete_node(self, store):
        store.add_node(Node(id="n1", name="test", project_id="p1"))
        assert store.delete_node("n1") is True
        assert store.get_node("n1") is None

    def test_delete_node_cascades_edges(self, store):
        store.add_node(Node(id="n1", name="a", project_id="p1"))
        store.add_node(Node(id="n2", name="b", project_id="p1"))
        store.add_edge(
            Edge(source_id="n1", target_id="n2", edge_type=EdgeType.CONTAINS, project_id="p1")
        )
        store.delete_node("n1")
        edges = store.get_edges(source_id="n1")
        assert len(edges) == 0

    def test_add_and_get_edge(self, store):
        store.add_node(Node(id="n1", project_id="p1"))
        store.add_node(Node(id="n2", project_id="p1"))
        store.add_edge(
            Edge(source_id="n1", target_id="n2", edge_type=EdgeType.IMPORTS, project_id="p1")
        )
        edges = store.get_edges(source_id="n1", project_id="p1")
        assert len(edges) == 1
        assert edges[0].edge_type == EdgeType.IMPORTS

    def test_bulk_edges(self, store):
        edges = [
            Edge(source_id=f"s{i}", target_id=f"t{i}", edge_type=EdgeType.CONTAINS, project_id="p1")
            for i in range(50)
        ]
        count = store.add_edges_bulk(edges)
        assert count == 50

    def test_get_neighbors_outgoing(self, store):
        store.add_node(Node(id="parent", name="parent", project_id="p1"))
        store.add_node(Node(id="child", name="child", project_id="p1"))
        store.add_edge(
            Edge(
                source_id="parent", target_id="child", edge_type=EdgeType.CONTAINS, project_id="p1"
            )
        )
        neighbors = store.get_neighbors("parent", direction="outgoing")
        assert len(neighbors) == 1
        assert neighbors[0][0].id == "child"

    def test_get_neighbors_incoming(self, store):
        store.add_node(Node(id="parent", name="parent", project_id="p1"))
        store.add_node(Node(id="child", name="child", project_id="p1"))
        store.add_edge(
            Edge(
                source_id="parent", target_id="child", edge_type=EdgeType.CONTAINS, project_id="p1"
            )
        )
        neighbors = store.get_neighbors("child", direction="incoming")
        assert len(neighbors) == 1
        assert neighbors[0][0].id == "parent"

    def test_project_meta(self, store):
        summary = ProjectSummary(project_id="p1", root_path="/test", name="Test", total_files=10)
        store.save_project_meta(summary)
        retrieved = store.get_project_meta("p1")
        assert retrieved is not None
        assert retrieved.name == "Test"
        assert retrieved.total_files == 10

    def test_list_projects(self, store):
        store.save_project_meta(ProjectSummary(project_id="p1", root_path="/a", name="A"))
        store.save_project_meta(ProjectSummary(project_id="p2", root_path="/b", name="B"))
        projects = store.list_projects()
        assert len(projects) == 2

    def test_delete_project(self, store):
        store.add_node(Node(id="n1", project_id="p1"))
        store.add_node(Node(id="n2", project_id="p1"))
        store.add_edge(
            Edge(source_id="n1", target_id="n2", edge_type=EdgeType.CONTAINS, project_id="p1")
        )
        store.save_project_meta(ProjectSummary(project_id="p1", root_path="/test", name="T"))
        deleted = store.delete_project("p1")
        assert deleted == 2
        assert store.get_project_meta("p1") is None

    def test_project_isolation(self, store):
        store.add_node(Node(id="n1", name="a", project_id="p1"))
        store.add_node(Node(id="n2", name="b", project_id="p2"))
        assert len(store.get_nodes(project_id="p1")) == 1
        assert len(store.get_nodes(project_id="p2")) == 1

    def test_stats(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.FILE, project_id="p1"))
        store.add_node(Node(id="n2", node_type=NodeType.CLASS, project_id="p1"))
        stats = store.stats("p1")
        assert stats["nodes"] == 2
        assert "FILE" in stats["node_types"]

    def test_filter_by_type(self, store):
        store.add_node(Node(id="f1", node_type=NodeType.FILE, project_id="p1"))
        store.add_node(Node(id="c1", node_type=NodeType.CLASS, project_id="p1"))
        files = store.get_nodes(project_id="p1", node_type=NodeType.FILE)
        assert len(files) == 1
        assert files[0].id == "f1"


# ---------------------------------------------------------------------------
# Scanner tests
# ---------------------------------------------------------------------------


class TestScanner:
    """Tests for the directory scanner."""

    def test_scan_creates_project_node(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        assert summary.project_id == scanner.project_id
        project_nodes = store.get_nodes(project_id=summary.project_id, node_type=NodeType.PROJECT)
        assert len(project_nodes) == 1

    def test_scan_creates_file_nodes(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        files = store.get_nodes(project_id=summary.project_id, node_type=NodeType.FILE)
        assert (
            len(files) >= 6
        )  # app.py, utils.py, test_app.py, index.js, package.json, README.md, config.yaml

    def test_scan_detects_languages(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        assert "python" in summary.languages
        assert "javascript" in summary.languages

    def test_scan_extracts_classes(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        assert summary.total_classes >= 3  # App, BaseHelper, AdvancedHelper

    def test_scan_extracts_functions(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        assert summary.total_functions >= 3  # main, helper, run, createApp

    def test_scan_extracts_tests(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        assert summary.total_tests >= 2  # test_init, test_run

    def test_scan_respects_max_files(self, sample_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(max_files=2)
        scanner = Scanner(str(sample_project), store, config)
        summary = scanner.scan()
        assert summary.total_files <= 2

    def test_scan_skips_hidden_dirs(self, sample_project):
        hidden = sample_project / ".hidden"
        hidden.mkdir()
        (hidden / "secret.py").write_text("x = 1\n", encoding="utf-8")
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        files = store.get_nodes(project_id=summary.project_id, node_type=NodeType.FILE)
        paths = [f.file_path for f in files]
        assert not any(".hidden" in p for p in paths)

    def test_scan_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            Scanner("/nonexistent/path", GraphStore(":memory:"))

    def test_scan_project_id_deterministic(self, sample_project):
        s1 = Scanner(str(sample_project), GraphStore(":memory:"))
        s2 = Scanner(str(sample_project), GraphStore(":memory:"))
        assert s1.project_id == s2.project_id

    def test_scan_creates_edges(self, sample_project):
        store = GraphStore(":memory:")
        scanner = Scanner(str(sample_project), store)
        summary = scanner.scan()
        edges = store.get_edges(project_id=summary.project_id)
        assert len(edges) > 0
        edge_types = {e.edge_type for e in edges}
        assert EdgeType.CONTAINS in edge_types


# ---------------------------------------------------------------------------
# Python analyzer tests
# ---------------------------------------------------------------------------


class TestPythonAnalyzer:
    """Tests for the Python AST analyzer."""

    def test_extracts_classes(self, scanned_store):
        store, pid = scanned_store
        classes = store.get_nodes(project_id=pid, node_type=NodeType.CLASS)
        names = {c.name for c in classes}
        assert "App" in names
        assert "BaseHelper" in names

    def test_extracts_functions(self, scanned_store):
        store, pid = scanned_store
        funcs = store.get_nodes(project_id=pid, node_type=NodeType.FUNCTION)
        names = {f.name for f in funcs}
        assert "main" in names
        assert "helper" in names

    def test_extracts_imports(self, scanned_store):
        store, pid = scanned_store
        imports = store.get_nodes(project_id=pid, node_type=NodeType.IMPORT)
        assert len(imports) > 0
        names = {i.name for i in imports}
        assert "os" in names or "json" in names

    def test_inheritance_edges(self, scanned_store):
        store, pid = scanned_store
        edges = store.get_edges(project_id=pid)
        inherit_edges = [e for e in edges if e.edge_type == EdgeType.INHERITS]
        assert len(inherit_edges) >= 1  # AdvancedHelper → BaseHelper

    def test_test_detection(self, scanned_store):
        store, pid = scanned_store
        tests = store.get_nodes(project_id=pid, node_type=NodeType.TEST)
        names = {t.name for t in tests}
        assert "test_init" in names or "TestApp" in names


# ---------------------------------------------------------------------------
# JavaScript analyzer tests
# ---------------------------------------------------------------------------


class TestJavaScriptAnalyzer:
    """Tests for the JS/TS regex analyzer."""

    def test_extracts_js_classes(self, scanned_store):
        store, pid = scanned_store
        classes = store.get_nodes(project_id=pid, node_type=NodeType.CLASS)
        names = {c.name for c in classes}
        assert "Widget" in names

    def test_extracts_js_functions(self, scanned_store):
        store, pid = scanned_store
        funcs = store.get_nodes(project_id=pid, node_type=NodeType.FUNCTION)
        names = {f.name for f in funcs}
        assert "createApp" in names

    def test_extracts_js_imports(self, scanned_store):
        store, pid = scanned_store
        imports = store.get_nodes(project_id=pid, node_type=NodeType.IMPORT)
        import_names = {i.name for i in imports}
        assert "react" in import_names


# ---------------------------------------------------------------------------
# Config analyzer tests
# ---------------------------------------------------------------------------


class TestConfigAnalyzer:
    """Tests for config file analysis."""

    def test_package_json_deps(self, scanned_store):
        store, pid = scanned_store
        deps = store.get_nodes(project_id=pid, node_type=NodeType.DEPENDENCY)
        names = {d.name for d in deps}
        assert "react" in names
        assert "express" in names

    def test_yaml_config_keys(self, scanned_store):
        store, pid = scanned_store
        configs = store.get_nodes(project_id=pid, node_type=NodeType.CONFIG)
        names = {c.name for c in configs}
        assert "database" in names or "logging" in names


# ---------------------------------------------------------------------------
# Doc analyzer tests
# ---------------------------------------------------------------------------


class TestDocAnalyzer:
    """Tests for documentation analysis."""

    def test_markdown_headings(self, scanned_store):
        store, pid = scanned_store
        docs = store.get_nodes(project_id=pid, node_type=NodeType.DOCUMENTATION)
        names = {d.name for d in docs}
        assert "Test Project" in names or "Installation" in names


# ---------------------------------------------------------------------------
# FTS search tests
# ---------------------------------------------------------------------------


class TestFTSSearch:
    """Tests for full-text search."""

    def test_basic_search(self, scanned_store):
        store, pid = scanned_store
        fts = FTSEngine(store)
        results = fts.search("App", project_id=pid)
        assert len(results) > 0

    def test_search_returns_scores(self, scanned_store):
        store, pid = scanned_store
        fts = FTSEngine(store)
        results = fts.search("helper", project_id=pid)
        assert all("score" in r for r in results)
        assert all(r["score"] > 0 for r in results)

    def test_search_by_name(self, scanned_store):
        store, pid = scanned_store
        fts = FTSEngine(store)
        nodes = fts.search_by_name("App", project_id=pid)
        assert len(nodes) > 0
        assert any(n.name == "App" for n in nodes)

    def test_search_empty_query(self, scanned_store):
        store, pid = scanned_store
        fts = FTSEngine(store)
        results = fts.search("", project_id=pid)
        assert results == []

    def test_search_with_type_filter(self, scanned_store):
        store, pid = scanned_store
        fts = FTSEngine(store)
        results = fts.search("App", project_id=pid, node_type=NodeType.CLASS)
        assert all(r["node"].node_type == NodeType.CLASS for r in results)


# ---------------------------------------------------------------------------
# Query engine tests
# ---------------------------------------------------------------------------


class TestQueryEngine:
    """Tests for the graph query engine."""

    def test_language_breakdown(self, scanned_store):
        store, pid = scanned_store
        qe = QueryEngine(store)
        langs = qe.language_breakdown(pid)
        assert "python" in langs
        assert "javascript" in langs

    def test_get_dependencies(self, scanned_store):
        store, pid = scanned_store
        qe = QueryEngine(store)
        deps = qe.get_dependencies(pid)
        names = {d["name"] for d in deps}
        assert "react" in names

    def test_get_tests(self, scanned_store):
        store, pid = scanned_store
        qe = QueryEngine(store)
        tests = qe.get_tests(pid)
        assert len(tests) >= 2

    def test_complexity_hotspots(self, scanned_store):
        store, pid = scanned_store
        qe = QueryEngine(store)
        spots = qe.complexity_hotspots(pid, top_n=5)
        assert len(spots) > 0
        assert "file" in spots[0]
        assert "score" in spots[0]

    def test_summary(self, scanned_store):
        store, pid = scanned_store
        qe = QueryEngine(store)
        data = qe.summary(pid)
        assert data["nodes"] > 0
        assert data["edges"] > 0

    def test_class_hierarchy(self, scanned_store):
        store, pid = scanned_store
        qe = QueryEngine(store)
        hierarchy = qe.get_class_hierarchy(pid)
        assert len(hierarchy) > 0

    def test_subgraph(self, scanned_store):
        store, pid = scanned_store
        # Get the project node as root
        project_nodes = store.get_nodes(project_id=pid, node_type=NodeType.PROJECT)
        assert len(project_nodes) == 1
        subgraph = QueryEngine(store).get_subgraph(project_nodes[0].id, max_depth=1)
        assert len(subgraph["nodes"]) > 0


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExport:
    """Tests for export formatters."""

    def test_to_json(self, scanned_store):
        store, pid = scanned_store
        exporter = GraphExporter(store)
        output = exporter.to_json(pid)
        data = json.loads(output)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0

    def test_to_dot(self, scanned_store):
        store, pid = scanned_store
        exporter = GraphExporter(store)
        output = exporter.to_dot(pid)
        assert "digraph project" in output
        assert "rankdir=LR" in output

    def test_to_markdown(self, scanned_store):
        store, pid = scanned_store
        exporter = GraphExporter(store)
        output = exporter.to_markdown(pid)
        assert "# Project Graph" in output
        assert "Files" in output


# ---------------------------------------------------------------------------
# CLI tests (via Click testing)
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the Click CLI commands."""

    def test_scan_command(self, sample_project):
        from click.testing import CliRunner

        from graphify.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["scan", str(sample_project), "--db", ":memory:"])
        assert result.exit_code == 0
        assert "Scan Complete" in result.output

    def test_stats_command(self, sample_project):
        from click.testing import CliRunner

        from graphify.cli import main

        # First scan
        store = GraphStore(str(sample_project / ".graphify.db"))
        scanner = Scanner(str(sample_project), store)
        scanner.scan()
        store.close()

        runner = CliRunner()
        result = runner.invoke(main, ["stats", str(sample_project)])
        assert result.exit_code == 0

    def test_search_command(self, sample_project):
        from click.testing import CliRunner

        from graphify.cli import main

        # First scan
        store = GraphStore(str(sample_project / ".graphify.db"))
        scanner = Scanner(str(sample_project), store)
        scanner.scan()
        store.close()

        runner = CliRunner()
        result = runner.invoke(main, ["search", "App", "--path", str(sample_project)])
        assert result.exit_code == 0

    def test_export_json_command(self, sample_project):
        from click.testing import CliRunner

        from graphify.cli import main

        store = GraphStore(str(sample_project / ".graphify.db"))
        scanner = Scanner(str(sample_project), store)
        scanner.scan()
        store.close()

        runner = CliRunner()
        result = runner.invoke(main, ["export", "json", str(sample_project)])
        assert result.exit_code == 0

    def test_hotspots_command(self, sample_project):
        from click.testing import CliRunner

        from graphify.cli import main

        store = GraphStore(str(sample_project / ".graphify.db"))
        scanner = Scanner(str(sample_project), store)
        scanner.scan()
        store.close()

        runner = CliRunner()
        result = runner.invoke(main, ["hotspots", str(sample_project)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Multi-project isolation tests
# ---------------------------------------------------------------------------


class TestMultiProjectIsolation:
    """Tests that multiple projects stay fully isolated."""

    def test_two_projects_no_cross_contamination(self, tmp_path):
        proj_a = tmp_path / "project_a"
        proj_b = tmp_path / "project_b"
        proj_a.mkdir()
        proj_b.mkdir()

        (proj_a / "a.py").write_text("class Alpha:\n    pass\n", encoding="utf-8")
        (proj_b / "b.py").write_text("class Beta:\n    pass\n", encoding="utf-8")

        store = GraphStore(":memory:")
        Scanner(str(proj_a), store).scan()
        Scanner(str(proj_b), store).scan()

        pid_a = generate_project_id(str(proj_a))
        pid_b = generate_project_id(str(proj_b))

        nodes_a = store.get_nodes(project_id=pid_a)
        nodes_b = store.get_nodes(project_id=pid_b)

        names_a = {n.name for n in nodes_a}
        names_b = {n.name for n in nodes_b}

        assert "Alpha" in names_a
        assert "Beta" not in names_a
        assert "Beta" in names_b
        assert "Alpha" not in names_b

    def test_delete_one_preserves_other(self, tmp_path):
        proj_a = tmp_path / "project_a"
        proj_b = tmp_path / "project_b"
        proj_a.mkdir()
        proj_b.mkdir()

        (proj_a / "a.py").write_text("class Alpha:\n    pass\n", encoding="utf-8")
        (proj_b / "b.py").write_text("class Beta:\n    pass\n", encoding="utf-8")

        store = GraphStore(":memory:")
        Scanner(str(proj_a), store).scan()
        Scanner(str(proj_b), store).scan()

        pid_a = generate_project_id(str(proj_a))
        pid_b = generate_project_id(str(proj_b))

        store.delete_project(pid_a)
        assert len(store.get_nodes(project_id=pid_a)) == 0
        assert len(store.get_nodes(project_id=pid_b)) > 0


# ---------------------------------------------------------------------------
# Obsidian export tests
# ---------------------------------------------------------------------------


class TestObsidianExport:
    """Tests for the Obsidian vault exporter."""

    def test_to_obsidian_creates_vault(self, scanned_store, tmp_path):
        """Should create a vault directory with notes and config."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")

        result = exporter.to_obsidian(pid, output_dir=vault_dir)

        assert result["notes_written"] > 0
        assert result["output_dir"] == str(Path(vault_dir))
        assert isinstance(result["folders"], list)
        assert len(result["folders"]) > 0
        assert Path(vault_dir).is_dir()

    def test_to_obsidian_index_exists(self, scanned_store, tmp_path):
        """Should generate _Index.md MOC."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")
        exporter.to_obsidian(pid, output_dir=vault_dir)

        index = Path(vault_dir) / "_Index.md"
        assert index.is_file()
        content = index.read_text(encoding="utf-8")
        assert "# 🗺️" in content
        assert "Overview" in content
        assert "Categories" in content

    def test_to_obsidian_graph_config(self, scanned_store, tmp_path):
        """Should generate .obsidian/ config files with graph colors."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")
        exporter.to_obsidian(pid, output_dir=vault_dir)

        obs_dir = Path(vault_dir) / ".obsidian"
        assert obs_dir.is_dir()

        graph_json = obs_dir / "graph.json"
        assert graph_json.is_file()
        graph_cfg = json.loads(graph_json.read_text(encoding="utf-8"))
        assert "colorGroups" in graph_cfg
        assert len(graph_cfg["colorGroups"]) > 0
        # Each color group has query and color keys
        cg = graph_cfg["colorGroups"][0]
        assert "query" in cg
        assert "color" in cg
        assert "rgb" in cg["color"]
        assert "a" in cg["color"]

        appearance = obs_dir / "appearance.json"
        assert appearance.is_file()
        app_cfg = json.loads(appearance.read_text(encoding="utf-8"))
        assert app_cfg.get("theme") == "obsidian"

        plugins = obs_dir / "core-plugins.json"
        assert plugins.is_file()
        plugins_list = json.loads(plugins.read_text(encoding="utf-8"))
        assert isinstance(plugins_list, list)
        assert "graph" in plugins_list

    def test_to_obsidian_notes_have_frontmatter(self, scanned_store, tmp_path):
        """Each note should have YAML frontmatter with type and tags."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")
        exporter.to_obsidian(pid, output_dir=vault_dir)

        md_files = list(Path(vault_dir).rglob("*.md"))
        # Exclude _Index.md
        note_files = [f for f in md_files if f.name != "_Index.md"]
        assert len(note_files) > 0

        for note in note_files[:5]:  # check first 5
            text = note.read_text(encoding="utf-8")
            assert text.startswith("---"), f"{note.name} missing frontmatter"
            # Should have closing ---
            parts = text.split("---", 2)
            assert len(parts) >= 3, f"{note.name} missing closing ---"
            # Frontmatter should contain type
            assert "type:" in parts[1]

    def test_to_obsidian_folder_structure(self, scanned_store, tmp_path):
        """Notes should be organized into typed folders."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")
        exporter.to_obsidian(pid, output_dir=vault_dir)

        vault = Path(vault_dir)
        # At least some of these folders should exist (scanned project has files, classes, functions)
        expected_some = {"Files", "Classes", "Functions"}
        existing = {d.name for d in vault.iterdir() if d.is_dir() and not d.name.startswith(".")}
        assert expected_some & existing, f"Expected some type folders, got {existing}"

    def test_to_obsidian_wikilinks(self, scanned_store, tmp_path):
        """Notes with edges should contain [[wikilinks]]."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")
        exporter.to_obsidian(pid, output_dir=vault_dir)

        all_text = ""
        for f in Path(vault_dir).rglob("*.md"):
            if f.name != "_Index.md":
                all_text += f.read_text(encoding="utf-8")

        # Scanned project should have some relationships → wikilinks
        assert "[[" in all_text and "]]" in all_text

    def test_to_obsidian_max_nodes(self, scanned_store, tmp_path):
        """max_nodes parameter should limit output."""
        store, pid = scanned_store
        exporter = GraphExporter(store)
        vault_dir = str(tmp_path / "vault")
        result = exporter.to_obsidian(pid, output_dir=vault_dir, max_nodes=3)
        assert result["notes_written"] <= 3

    def test_export_obsidian_cli_command(self, sample_project):
        """CLI 'export obsidian' should create vault directory."""
        from click.testing import CliRunner

        from graphify.cli import main

        store = GraphStore(str(sample_project / ".graphify.db"))
        scanner = Scanner(str(sample_project), store)
        scanner.scan()
        store.close()

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "result")
            result = runner.invoke(
                main,
                ["export", "obsidian", str(sample_project), "--output", out],
            )
            assert result.exit_code == 0, result.output
            assert Path(out).is_dir() or any(
                Path(td).rglob("*.md"),
            )
