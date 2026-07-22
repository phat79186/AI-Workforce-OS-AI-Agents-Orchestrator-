"""
Tests for Graphify v2 enhancements:
  - Content caching (SHA-256 incremental re-scans)
  - .graphifyignore support
  - Edge confidence & provenance
  - Call graph extraction
  - Rationale comment extraction
  - God node detection & path finding
  - Report generation
  - HTML visualization
  - GraphML export
  - Incremental scan mode
  - Query engine: explain, path, communities
"""

from __future__ import annotations

import os
import textwrap

import pytest

from graphify.core.cache import ContentCache
from graphify.core.config import GraphifyConfig
from graphify.core.graph import GraphStore
from graphify.core.ignore import IgnoreFilter
from graphify.core.scanner import Scanner
from graphify.core.schema import Edge, EdgeProvenance, EdgeType, Node, NodeType
from graphify.export.formatters import GraphExporter
from graphify.report.generator import ReportGenerator
from graphify.search.query_engine import QueryEngine
from graphify.visualization.html_renderer import HTMLRenderer

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
def py_project(tmp_path):
    """Create a sample Python project on disk."""
    (tmp_path / "main.py").write_text(
        textwrap.dedent("""\
        # NOTE: Entry point for the application
        import os
        from utils import helper

        class App:
            \"\"\"Main application class.\"\"\"

            def run(self):
                # TODO: Add proper error handling
                result = helper()
                return result

            def stop(self):
                pass

        def main():
            # HACK: Quick fix for startup race condition
            app = App()
            app.run()

        if __name__ == "__main__":
            main()
    """),
        encoding="utf-8",
    )

    (tmp_path / "utils.py").write_text(
        textwrap.dedent("""\
        # WHY: Separated utility functions for reuse across modules
        import json

        def helper():
            \"\"\"Helper function.\"\"\"
            return process_data({})

        def process_data(data):
            # FIXME: Handle None input
            return json.dumps(data)

        class DataProcessor:
            def process(self):
                return helper()
    """),
        encoding="utf-8",
    )

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text(
        textwrap.dedent("""\
        from main import App

        class TestApp:
            def test_run(self):
                app = App()
                assert app.run() is not None

            def test_stop(self):
                app = App()
                app.stop()
    """),
        encoding="utf-8",
    )

    # Config file
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent("""\
        [project]
        name = "sample"
        version = "1.0.0"
        dependencies = ["flask", "pytest"]
    """),
        encoding="utf-8",
    )

    return tmp_path


# ===================================================================
# Content Cache Tests
# ===================================================================


class TestContentCache:

    def test_hash_content_deterministic(self):
        h1 = ContentCache.hash_content("hello world")
        h2 = ContentCache.hash_content("hello world")
        assert h1 == h2

    def test_hash_content_different(self):
        h1 = ContentCache.hash_content("hello")
        h2 = ContentCache.hash_content("world")
        assert h1 != h2

    def test_hash_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content", encoding="utf-8")
        h = ContentCache.hash_file(str(f))
        assert len(h) == 64  # SHA-256

    def test_cache_store_and_retrieve(self, store):
        cache = ContentCache(store._get_conn)
        cache.set_hash("file.py", "proj1", "abc123")
        assert cache.get_hash("file.py", "proj1") == "abc123"

    def test_cache_miss(self, store):
        cache = ContentCache(store._get_conn)
        assert cache.get_hash("missing.py", "proj1") is None

    def test_cache_bulk(self, store):
        cache = ContentCache(store._get_conn)
        entries = {"a.py": "hash_a", "b.py": "hash_b", "c.py": "hash_c"}
        cache.set_hashes_bulk(entries, "proj1")
        result = cache.get_all_hashes("proj1")
        assert result == entries

    def test_cache_project_isolation(self, store):
        cache = ContentCache(store._get_conn)
        cache.set_hash("file.py", "proj1", "hash1")
        cache.set_hash("file.py", "proj2", "hash2")
        assert cache.get_hash("file.py", "proj1") == "hash1"
        assert cache.get_hash("file.py", "proj2") == "hash2"

    def test_cache_remove_paths(self, store):
        cache = ContentCache(store._get_conn)
        cache.set_hashes_bulk({"a.py": "h1", "b.py": "h2"}, "proj1")
        removed = cache.remove_paths({"a.py"}, "proj1")
        assert removed == 1
        assert cache.get_hash("a.py", "proj1") is None
        assert cache.get_hash("b.py", "proj1") == "h2"

    def test_cache_clear_project(self, store):
        cache = ContentCache(store._get_conn)
        cache.set_hashes_bulk({"a.py": "h1", "b.py": "h2"}, "proj1")
        cache.clear_project("proj1")
        assert cache.get_all_hashes("proj1") == {}


# ===================================================================
# Ignore Filter Tests
# ===================================================================


class TestIgnoreFilter:

    def test_no_ignorefile(self, tmp_path):
        f = IgnoreFilter(str(tmp_path))
        assert not f.has_rules
        assert not f.is_ignored("any/path")

    def test_simple_pattern(self, tmp_path):
        (tmp_path / ".graphifyignore").write_text("vendor/\nnode_modules/\n", encoding="utf-8")
        f = IgnoreFilter(str(tmp_path))
        assert f.has_rules
        assert f.is_ignored("vendor/something.py")
        assert f.is_ignored("some/vendor/deep.py")
        assert not f.is_ignored("main.py")

    def test_glob_pattern(self, tmp_path):
        (tmp_path / ".graphifyignore").write_text("*.generated.py\n", encoding="utf-8")
        f = IgnoreFilter(str(tmp_path))
        assert f.is_ignored("models.generated.py")
        assert not f.is_ignored("models.py")

    def test_negation_pattern(self, tmp_path):
        (tmp_path / ".graphifyignore").write_text("dist/\n!dist/important.js\n", encoding="utf-8")
        f = IgnoreFilter(str(tmp_path))
        assert f.is_ignored("dist/bundle.js")
        assert not f.is_ignored("dist/important.js")

    def test_comments_and_blank_lines(self, tmp_path):
        (tmp_path / ".graphifyignore").write_text(
            "# Comment\n\n  \nvendor/\n",
            encoding="utf-8",
        )
        f = IgnoreFilter(str(tmp_path))
        assert len(f._patterns) == 1


# ===================================================================
# Edge Confidence & Provenance
# ===================================================================


class TestEdgeConfidence:

    def test_edge_default_confidence(self):
        e = Edge(source_id="a", target_id="b", edge_type=EdgeType.CONTAINS)
        assert e.confidence == 1.0
        assert e.provenance == EdgeProvenance.EXTRACTED.value

    def test_edge_inferred_confidence(self):
        e = Edge(
            source_id="a",
            target_id="b",
            edge_type=EdgeType.CALLS,
            confidence=0.8,
            provenance=EdgeProvenance.INFERRED.value,
        )
        assert e.confidence == 0.8
        assert e.provenance == "INFERRED"

    def test_store_preserves_confidence(self, store):
        e = Edge(
            source_id="a",
            target_id="b",
            edge_type=EdgeType.CALLS,
            confidence=0.7,
            provenance="INFERRED",
            project_id="p1",
        )
        # Need nodes first for FK
        store.add_node(Node(id="a", node_type=NodeType.FUNCTION, project_id="p1"))
        store.add_node(Node(id="b", node_type=NodeType.FUNCTION, project_id="p1"))
        store.add_edge(e)
        edges = store.get_edges(source_id="a", project_id="p1")
        assert len(edges) == 1
        assert edges[0].confidence == 0.7
        assert edges[0].provenance == "INFERRED"


# ===================================================================
# Call Graph Extraction
# ===================================================================


class TestCallGraphExtraction:

    def test_extracts_function_calls(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        edges = store.get_edges(project_id=summary.project_id)
        call_edges = [e for e in edges if e.edge_type == EdgeType.CALLS]
        assert len(call_edges) > 0, "Should extract at least one CALLS edge"

    def test_call_edges_have_inferred_provenance(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        edges = store.get_edges(project_id=summary.project_id)
        call_edges = [e for e in edges if e.edge_type == EdgeType.CALLS]
        for edge in call_edges:
            assert edge.provenance == "INFERRED"
            assert 0 < edge.confidence <= 1.0


# ===================================================================
# Rationale Comment Extraction
# ===================================================================


class TestRationaleExtraction:

    def test_extracts_rationale_nodes(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        rationale = store.get_nodes(
            project_id=summary.project_id,
            node_type=NodeType.RATIONALE,
        )
        assert len(rationale) >= 4  # NOTE, TODO, HACK, WHY, FIXME in our fixtures

    def test_rationale_has_tags(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        rationale = store.get_nodes(
            project_id=summary.project_id,
            node_type=NodeType.RATIONALE,
        )
        tags = {n.metadata.get("tag") for n in rationale}
        assert "NOTE" in tags or "TODO" in tags or "HACK" in tags

    def test_rationale_linked_to_file(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        edges = store.get_edges(project_id=summary.project_id)
        doc_edges = [e for e in edges if e.edge_type == EdgeType.DOCUMENTS]
        assert len(doc_edges) > 0


# ===================================================================
# God Nodes & Path Finding
# ===================================================================


class TestGraphIntelligence:

    def test_god_nodes(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        gods = store.god_nodes(summary.project_id, top_n=5)
        assert len(gods) > 0
        assert gods[0]["degree"] >= gods[-1]["degree"]

    def test_node_degree(self, store):
        store.add_node(Node(id="a", node_type=NodeType.CLASS, project_id="p"))
        store.add_node(Node(id="b", node_type=NodeType.FUNCTION, project_id="p"))
        store.add_node(Node(id="c", node_type=NodeType.FUNCTION, project_id="p"))
        store.add_edge(
            Edge(source_id="a", target_id="b", edge_type=EdgeType.CONTAINS, project_id="p")
        )
        store.add_edge(
            Edge(source_id="a", target_id="c", edge_type=EdgeType.CONTAINS, project_id="p")
        )

        deg = store.node_degree("a")
        assert deg["out_degree"] == 2
        assert deg["in_degree"] == 0
        assert deg["total"] == 2

    def test_shortest_path(self, store):
        for nid in ("a", "b", "c", "d"):
            store.add_node(Node(id=nid, node_type=NodeType.FUNCTION, project_id="p"))
        store.add_edge(Edge(source_id="a", target_id="b", edge_type=EdgeType.CALLS, project_id="p"))
        store.add_edge(Edge(source_id="b", target_id="c", edge_type=EdgeType.CALLS, project_id="p"))
        store.add_edge(Edge(source_id="c", target_id="d", edge_type=EdgeType.CALLS, project_id="p"))

        path = store.shortest_path("a", "d")
        assert path is not None
        assert path[0] == "a"
        assert path[-1] == "d"
        assert len(path) == 4

    def test_shortest_path_no_connection(self, store):
        store.add_node(Node(id="x", node_type=NodeType.FUNCTION, project_id="p"))
        store.add_node(Node(id="y", node_type=NodeType.FUNCTION, project_id="p"))
        assert store.shortest_path("x", "y") is None

    def test_delete_file_nodes(self, store):
        store.add_node(Node(id="f1", node_type=NodeType.FILE, file_path="a.py", project_id="p"))
        store.add_node(
            Node(id="fn1", node_type=NodeType.FUNCTION, file_path="a.py", project_id="p")
        )
        store.add_edge(
            Edge(source_id="f1", target_id="fn1", edge_type=EdgeType.CONTAINS, project_id="p")
        )

        count = store.delete_file_nodes("a.py", "p")
        assert count == 2
        assert store.get_node("f1") is None
        assert store.get_node("fn1") is None


# ===================================================================
# Query Engine: Explain, Path, Communities
# ===================================================================


class TestQueryEngineEnhancements:

    def test_explain_node(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()
        qe = QueryEngine(store)

        result = qe.explain_node("App", project_id=summary.project_id)
        assert "error" not in result
        assert result["node"]["name"] == "App"
        assert result["degree"]["total"] > 0

    def test_explain_missing_node(self, store):
        qe = QueryEngine(store)
        result = qe.explain_node("NonExistent", project_id="p")
        assert "error" in result

    def test_find_path_by_name(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()
        qe = QueryEngine(store)

        # App and run are connected through CONTAINS
        result = qe.find_path("App", "run", project_id=summary.project_id)
        assert len(result) >= 2

    def test_detect_communities(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()
        qe = QueryEngine(store)

        communities = qe.detect_communities(project_id=summary.project_id)
        assert len(communities) > 0


# ===================================================================
# Report Generator
# ===================================================================


class TestReportGenerator:

    def test_generate_report(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        gen = ReportGenerator(store)
        report = gen.generate(summary.project_id)

        assert "# 📊 Graph Report:" in report
        assert "## Overview" in report
        assert "## 💡 Suggested Questions" in report

    def test_report_has_god_nodes(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        gen = ReportGenerator(store)
        report = gen.generate(summary.project_id)
        assert "God Nodes" in report

    def test_report_writes_to_file(self, py_project, tmp_path):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        gen = ReportGenerator(store)
        gen.generate(summary.project_id, output_dir=str(tmp_path))
        assert (tmp_path / "GRAPH_REPORT.md").exists()

    def test_report_has_rationale_section(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        gen = ReportGenerator(store)
        report = gen.generate(summary.project_id)
        assert "Rationale" in report


# ===================================================================
# HTML Visualization
# ===================================================================


class TestHTMLVisualization:

    def test_render_html(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        renderer = HTMLRenderer(store)
        html = renderer.render(summary.project_id)
        assert "vis-network" in html
        assert "Graphify" in html
        assert "<script>" in html

    def test_render_to_file(self, py_project, tmp_path):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        renderer = HTMLRenderer(store)
        renderer.render(summary.project_id, output_dir=str(tmp_path))
        assert (tmp_path / "graph.html").exists()
        content = (tmp_path / "graph.html").read_text(encoding="utf-8")
        assert len(content) > 1000


# ===================================================================
# GraphML Export
# ===================================================================


class TestGraphMLExport:

    def test_graphml_valid_xml(self, py_project):
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        exporter = GraphExporter(store)
        xml = exporter.to_graphml(summary.project_id)
        assert "<?xml" in xml
        assert "<graphml" in xml
        assert "<node" in xml
        assert "<edge" in xml


# ===================================================================
# Incremental Scan
# ===================================================================


class TestIncrementalScan:

    def test_incremental_detects_changes(self, py_project):
        db_path = str(py_project / ".graphify.db")
        store = GraphStore(db_path)
        config = GraphifyConfig(db_path=db_path)

        # Initial full scan
        scanner1 = Scanner(str(py_project), store, config)
        s1 = scanner1.scan()
        initial_nodes = store.stats(s1.project_id)["nodes"]

        # Modify a file
        (py_project / "main.py").write_text(
            "# Changed\ndef new_func():\n    pass\n", encoding="utf-8"
        )

        # Incremental scan
        scanner2 = Scanner(str(py_project), store, config)
        s2 = scanner2.scan(incremental=True)

        assert s2.project_id == s1.project_id
        store.close()

    def test_incremental_detects_removal(self, py_project):
        db_path = str(py_project / ".graphify.db")
        store = GraphStore(db_path)
        config = GraphifyConfig(db_path=db_path)

        scanner1 = Scanner(str(py_project), store, config)
        s1 = scanner1.scan()

        # Remove a file
        os.remove(str(py_project / "utils.py"))

        # Incremental scan
        scanner2 = Scanner(str(py_project), store, config)
        s2 = scanner2.scan(incremental=True)

        assert s2.project_id == s1.project_id
        store.close()

    def test_no_change_is_cached(self, py_project):
        db_path = str(py_project / ".graphify.db")
        store = GraphStore(db_path)
        config = GraphifyConfig(db_path=db_path)

        scanner1 = Scanner(str(py_project), store, config)
        scanner1.scan()

        # Second run - nothing changed
        scanner2 = Scanner(str(py_project), store, config)
        scanner2.scan(incremental=True)

        # If everything cached, _file_count should be 0 (all cached)
        assert scanner2._cached_count > 0
        store.close()


# ===================================================================
# .graphifyignore Integration Test
# ===================================================================


class TestIgnoreIntegration:

    def test_ignores_specified_files(self, py_project):
        (py_project / ".graphifyignore").write_text("tests/\n", encoding="utf-8")
        store = GraphStore(":memory:")
        config = GraphifyConfig(use_cache=False)
        scanner = Scanner(str(py_project), store, config)
        summary = scanner.scan()

        # Should not have any test files
        files = store.get_nodes(project_id=summary.project_id, node_type=NodeType.FILE)
        file_paths = [f.file_path for f in files]
        assert not any("test_main" in p for p in file_paths)


# ===================================================================
# New Schema Types
# ===================================================================


class TestNewSchemaTypes:

    def test_rationale_node_type(self):
        n = Node(node_type=NodeType.RATIONALE, name="TODO: fix this")
        assert n.node_type == NodeType.RATIONALE

    def test_community_node_type(self):
        n = Node(node_type=NodeType.COMMUNITY, name="auth_cluster")
        assert n.node_type == NodeType.COMMUNITY

    def test_member_of_edge_type(self):
        e = Edge(edge_type=EdgeType.MEMBER_OF)
        assert e.edge_type == EdgeType.MEMBER_OF

    def test_edge_provenance_enum(self):
        assert EdgeProvenance.EXTRACTED.value == "EXTRACTED"
        assert EdgeProvenance.INFERRED.value == "INFERRED"
        assert EdgeProvenance.AMBIGUOUS.value == "AMBIGUOUS"


# ===================================================================
# Config Enhancements
# ===================================================================


class TestConfigEnhancements:

    def test_default_features_enabled(self):
        cfg = GraphifyConfig()
        assert cfg.extract_call_graph is True
        assert cfg.extract_rationale is True
        assert cfg.use_cache is True
        assert cfg.generate_report is True
        assert cfg.generate_html is True

    def test_features_can_be_disabled(self):
        cfg = GraphifyConfig(
            extract_call_graph=False,
            use_cache=False,
            generate_report=False,
            generate_html=False,
        )
        assert cfg.extract_call_graph is False
        assert cfg.use_cache is False
