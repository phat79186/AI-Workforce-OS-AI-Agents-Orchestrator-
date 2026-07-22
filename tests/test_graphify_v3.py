"""
Tests for Graphify v3 enhancements:
  - Custom exception hierarchy
  - Input validation & path safety
  - Database migrations
  - Scan metrics
  - Graph diffing & snapshots
  - File watcher
  - Context manager support
  - API hardening (CORS, error handling)
"""

from __future__ import annotations

import os
import textwrap
import time

import pytest

from graphify.core.cache import ContentCache
from graphify.core.config import GraphifyConfig
from graphify.core.differ import GraphDiff, GraphDiffer
from graphify.core.exceptions import (
    AnalysisError,
    ConfigError,
    ExportError,
    GraphError,
    GraphifyError,
    NodeNotFoundError,
    PathTraversalError,
    RenderError,
    ScanError,
    SchemaVersionError,
    ValidationError,
    WatchError,
)
from graphify.core.graph import GraphStore
from graphify.core.metrics import MetricsStore, ScanMetrics
from graphify.core.migrations import LATEST_VERSION, get_current_version, migrate
from graphify.core.scanner import Scanner
from graphify.core.schema import Edge, EdgeType, Node, NodeType
from graphify.core.validation import (
    sanitize_search_query,
    validate_node_name,
    validate_path,
    validate_positive_int,
    validate_project_id,
)
from graphify.core.watcher import FileWatcher

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
    (tmp_path / "app.py").write_text(
        textwrap.dedent("""\
        # NOTE: Main application entry point
        class Server:
            def start(self):
                # TODO: Add graceful shutdown
                pass
            def stop(self):
                pass
        def main():
            s = Server()
            s.start()
    """),
        encoding="utf-8",
    )
    (tmp_path / "utils.py").write_text(
        textwrap.dedent("""\
        import json
        def helper():
            return json.dumps({})
    """),
        encoding="utf-8",
    )
    return tmp_path


# ===================================================================
# Exception hierarchy tests
# ===================================================================


class TestExceptions:

    def test_base_exception(self):
        exc = GraphifyError("test")
        assert str(exc) == "test"
        assert exc.code == "GRAPHIFY_ERROR"

    def test_scan_error(self):
        exc = ScanError("scan failed", path="/tmp/x")
        assert exc.path == "/tmp/x"
        assert exc.code == "SCAN_ERROR"
        assert isinstance(exc, GraphifyError)

    def test_analysis_error(self):
        exc = AnalysisError("parse failed", file_path="a.py", analyzer="python")
        assert exc.file_path == "a.py"
        assert exc.analyzer == "python"

    def test_graph_error(self):
        exc = GraphError("db locked")
        assert exc.code == "GRAPH_ERROR"

    def test_schema_version_error(self):
        exc = SchemaVersionError(expected=3, actual=1)
        assert exc.expected == 3
        assert exc.actual == 1
        assert "mismatch" in str(exc)

    def test_node_not_found_error(self):
        exc = NodeNotFoundError("abc123")
        assert exc.node_id == "abc123"

    def test_config_error(self):
        exc = ConfigError("missing key")
        assert exc.code == "CONFIG_ERROR"

    def test_export_error(self):
        exc = ExportError("too large", fmt="json")
        assert exc.format == "json"

    def test_render_error(self):
        exc = RenderError("template missing")
        assert exc.code == "RENDER_ERROR"

    def test_validation_error(self):
        exc = ValidationError("bad input", field="name")
        assert exc.field == "name"

    def test_path_traversal_error(self):
        exc = PathTraversalError("/etc/passwd", "/home/user")
        assert exc.path == "/etc/passwd"
        assert exc.root == "/home/user"
        assert "traversal" in str(exc).lower()

    def test_watch_error(self):
        exc = WatchError("inotify limit")
        assert exc.code == "WATCH_ERROR"

    def test_hierarchy(self):
        """All errors should be catchable as GraphifyError."""
        errors = [
            ScanError(),
            AnalysisError(),
            GraphError(),
            ConfigError(),
            ExportError(),
            RenderError(),
            ValidationError(),
            WatchError(),
        ]
        for exc in errors:
            assert isinstance(exc, GraphifyError)


# ===================================================================
# Validation tests
# ===================================================================


class TestValidation:

    def test_validate_path_normal(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1", encoding="utf-8")
        result = validate_path(str(f))
        assert os.path.isabs(result)

    def test_validate_path_empty(self):
        with pytest.raises(ValidationError, match="empty"):
            validate_path("")

    def test_validate_path_traversal(self, tmp_path):
        with pytest.raises(PathTraversalError):
            validate_path("/etc/passwd", root=str(tmp_path))

    def test_validate_path_within_root(self, tmp_path):
        child = tmp_path / "sub" / "file.py"
        child.parent.mkdir()
        child.write_text("x = 1", encoding="utf-8")
        result = validate_path(str(child), root=str(tmp_path))
        assert result.startswith(str(tmp_path))

    def test_validate_project_id_valid(self):
        assert validate_project_id("abcdef123456") == "abcdef123456"

    def test_validate_project_id_empty(self):
        assert validate_project_id("") == ""

    def test_validate_project_id_invalid(self):
        with pytest.raises(ValidationError):
            validate_project_id("not-hex!")

    def test_validate_positive_int(self):
        assert validate_positive_int(5, "limit") == 5

    def test_validate_positive_int_zero(self):
        with pytest.raises(ValidationError):
            validate_positive_int(0, "limit")

    def test_validate_positive_int_too_large(self):
        with pytest.raises(ValidationError):
            validate_positive_int(999999, "limit", max_val=1000)

    def test_validate_node_name(self):
        assert validate_node_name("  App  ") == "App"

    def test_validate_node_name_empty(self):
        with pytest.raises(ValidationError):
            validate_node_name("")

    def test_sanitize_search_query(self):
        assert sanitize_search_query("class User") == "class User"

    def test_sanitize_search_query_strips_quotes(self):
        result = sanitize_search_query('test "injection')
        assert '"' not in result

    def test_sanitize_search_query_empty(self):
        with pytest.raises(ValidationError):
            sanitize_search_query("")


# ===================================================================
# Migration tests
# ===================================================================


class TestMigrations:

    def test_latest_version(self):
        assert LATEST_VERSION >= 3

    def test_migrate_fresh_db(self, store):
        conn = store._get_conn()
        version = get_current_version(conn)
        # After GraphStore init, migrations should have run
        assert version >= 2

    def test_migrate_idempotent(self, store):
        conn = store._get_conn()
        v1 = migrate(conn, target=LATEST_VERSION)
        v2 = migrate(conn, target=LATEST_VERSION)
        assert v1 == v2

    def test_scan_metrics_table_exists(self, store):
        conn = store._get_conn()
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "scan_metrics" in tables
        assert "graph_snapshots" in tables


# ===================================================================
# Scan metrics tests
# ===================================================================


class TestScanMetrics:

    def test_metrics_dataclass(self):
        m = ScanMetrics(project_id="p1", files_total=10, files_cached=8)
        m.start()
        time.sleep(0.01)
        m.stop()
        m.compute_cache_rate()
        assert m.duration_s > 0
        assert m.cache_hit_rate == 0.8

    def test_metrics_to_dict(self):
        m = ScanMetrics(project_id="p1", files_total=5)
        d = m.to_dict()
        assert d["project_id"] == "p1"
        assert "duration_s" in d

    def test_metrics_record_analyzer(self):
        m = ScanMetrics()
        m.record_analyzer("python", 15.5)
        m.record_analyzer("python", 10.0)
        assert m.analyzer_ms["python"] == 25.5

    def test_metrics_store_save_and_history(self, store):
        ms = MetricsStore(store._get_conn)
        m = ScanMetrics(project_id="p1", files_total=10, duration_s=1.5)
        m.started_at = time.time()
        ms.save(m)
        history = ms.history("p1")
        assert len(history) == 1
        assert history[0]["files_total"] == 10

    def test_metrics_store_latest(self, store):
        ms = MetricsStore(store._get_conn)
        m = ScanMetrics(project_id="p1", files_total=5)
        m.started_at = time.time()
        ms.save(m)
        latest = ms.latest("p1")
        assert latest is not None
        assert latest["files_total"] == 5

    def test_metrics_store_averages(self, store):
        ms = MetricsStore(store._get_conn)
        for i in range(5):
            m = ScanMetrics(project_id="p1", files_total=10 + i, duration_s=float(i))
            m.started_at = time.time()
            ms.save(m)
        avgs = ms.averages("p1")
        assert avgs["total_scans"] == 5
        assert avgs["avg_files_total"] > 0

    def test_metrics_empty_project(self, store):
        ms = MetricsStore(store._get_conn)
        assert ms.latest("nonexistent") is None
        assert ms.averages("nonexistent") == {}


# ===================================================================
# Graph differ tests
# ===================================================================


class TestGraphDiffer:

    def test_take_snapshot(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.CLASS, project_id="p1"))
        differ = GraphDiffer(store._get_conn)
        snap_id = differ.take_snapshot("p1", label="v1")
        assert snap_id > 0

    def test_list_snapshots(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.CLASS, project_id="p1"))
        differ = GraphDiffer(store._get_conn)
        differ.take_snapshot("p1", label="v1")
        differ.take_snapshot("p1", label="v2")
        snaps = differ.list_snapshots("p1")
        assert len(snaps) == 2
        assert snaps[0]["label"] == "v2"  # most recent first

    def test_diff_snapshots_no_changes(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.CLASS, project_id="p1"))
        differ = GraphDiffer(store._get_conn)
        s1 = differ.take_snapshot("p1", label="before")
        s2 = differ.take_snapshot("p1", label="after")
        diff = differ.diff_snapshots(s1, s2)
        assert not diff.has_changes

    def test_diff_detects_added_node(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.CLASS, project_id="p1"))
        differ = GraphDiffer(store._get_conn)
        s1 = differ.take_snapshot("p1", label="before")
        store.add_node(Node(id="n2", node_type=NodeType.FUNCTION, project_id="p1", name="new_fn"))
        s2 = differ.take_snapshot("p1", label="after")
        diff = differ.diff_snapshots(s1, s2)
        assert diff.has_changes
        assert len(diff.nodes_added) == 1
        assert diff.summary["nodes_added"] == 1

    def test_diff_detects_removed_node(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.CLASS, project_id="p1"))
        store.add_node(Node(id="n2", node_type=NodeType.FUNCTION, project_id="p1"))
        differ = GraphDiffer(store._get_conn)
        s1 = differ.take_snapshot("p1")
        store._get_conn().execute("DELETE FROM nodes WHERE id = 'n2'")
        store._get_conn().commit()
        s2 = differ.take_snapshot("p1")
        diff = differ.diff_snapshots(s1, s2)
        assert len(diff.nodes_removed) == 1

    def test_diff_to_dict(self, store):
        differ = GraphDiffer(store._get_conn)
        diff = GraphDiff(project_id="p1", before_label="a", after_label="b")
        d = diff.to_dict()
        assert d["project_id"] == "p1"
        assert "summary" in d

    def test_diff_current(self, store):
        store.add_node(Node(id="n1", node_type=NodeType.CLASS, project_id="p1"))
        differ = GraphDiffer(store._get_conn)
        s1 = differ.take_snapshot("p1")
        store.add_node(Node(id="n2", node_type=NodeType.FUNCTION, project_id="p1"))
        diff = differ.diff_current("p1", s1)
        assert diff.has_changes


# ===================================================================
# Context manager tests
# ===================================================================


class TestContextManager:

    def test_store_as_context_manager(self):
        with GraphStore(":memory:") as store:
            store.add_node(Node(id="n1", node_type=NodeType.CLASS))
            assert store.get_node("n1") is not None
        assert store._closed

    def test_store_context_manager_closes(self):
        store = GraphStore(":memory:")
        store.__enter__()
        store.__exit__(None, None, None)
        assert store._closed


# ===================================================================
# File watcher tests
# ===================================================================


class TestFileWatcher:

    def test_watcher_init(self, tmp_path):
        watcher = FileWatcher(str(tmp_path))
        # Not yet stopped — is_running reflects the stop_event flag
        assert watcher.is_running

    def test_watcher_invalid_path(self):
        with pytest.raises(WatchError):
            FileWatcher("/nonexistent/path")

    def test_watcher_relevance_filter(self, tmp_path):
        watcher = FileWatcher(str(tmp_path))
        assert watcher._is_relevant(str(tmp_path / "main.py"))
        assert not watcher._is_relevant(str(tmp_path / ".git" / "config"))
        assert not watcher._is_relevant(str(tmp_path / "node_modules" / "x.js"))

    def test_watcher_enqueue_and_flush(self, tmp_path):
        received = []
        watcher = FileWatcher(str(tmp_path), on_change=lambda paths: received.extend(paths))
        watcher._enqueue(str(tmp_path / "test.py"))
        watcher._flush()
        assert "test.py" in received

    def test_watcher_stop(self, tmp_path):
        watcher = FileWatcher(str(tmp_path))
        watcher.stop()
        assert not watcher.is_running


# ===================================================================
# Integration: scan with metrics
# ===================================================================


class TestScanWithMetrics:

    def test_full_scan_produces_nodes(self, py_project):
        with GraphStore(":memory:") as store:
            config = GraphifyConfig(use_cache=False)
            scanner = Scanner(str(py_project), store, config)
            summary = scanner.scan()
            assert summary.total_files >= 2
            assert summary.total_lines > 0
            nodes = store.get_nodes(project_id=summary.project_id)
            assert len(nodes) > 0
