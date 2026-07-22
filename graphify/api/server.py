"""
Graphify REST API — production-ready Flask server.

Features:
  - Configurable CORS (defaults to ``*`` for development)
  - Global error handling with structured JSON (no internal details leaked)
  - Per-app state via ``app.extensions`` (no module-level globals)
  - Metrics, snapshot, and diff endpoints

Start with: ``python -m graphify serve --db /path/to/.graphify.db``
"""

from __future__ import annotations

import logging

from graphify.core.differ import GraphDiffer
from graphify.core.exceptions import GraphifyError, ValidationError
from graphify.core.graph import GraphStore
from graphify.core.metrics import MetricsStore
from graphify.export.formatters import GraphExporter
from graphify.search.fts_engine import FTSEngine
from graphify.search.query_engine import QueryEngine

logger = logging.getLogger(__name__)


def _safe_int(value: str | None, default: int, lo: int = 1, hi: int = 500) -> int:
    """Parse an integer query param within bounds."""
    if value is None:
        return default
    try:
        n = int(value)
    except (ValueError, TypeError):
        return default
    return max(lo, min(n, hi))


def _ext(key: str):
    """Retrieve extension from the current Flask app."""
    from flask import current_app  # pylint: disable=C0415

    return current_app.extensions[key]


def create_app(  # noqa: C901  # pylint: disable=undefined-variable
    db_path: str = ":memory:",
    allowed_origins: str = "*",
) -> Flask:  # type: ignore[name-defined]  # noqa: F821
    """Create and configure the Flask application."""
    from flask import Flask, jsonify, request  # pylint: disable=C0415

    app = Flask(__name__)

    store = GraphStore(db_path)
    app.extensions["gfx_store"] = store
    app.extensions["gfx_fts"] = FTSEngine(store)
    app.extensions["gfx_query"] = QueryEngine(store)
    app.extensions["gfx_exporter"] = GraphExporter(store)
    app.extensions["gfx_metrics"] = MetricsStore(store.get_connection_factory())
    app.extensions["gfx_differ"] = GraphDiffer(store.get_connection_factory())
    app.extensions["gfx_db_path"] = db_path

    import atexit  # pylint: disable=C0415

    atexit.register(store.close)

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    @app.after_request
    def _add_cors(response):
        response.headers["Access-Control-Allow-Origin"] = allowed_origins
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # ------------------------------------------------------------------
    # Global error handling
    # ------------------------------------------------------------------

    @app.errorhandler(ValidationError)
    def _handle_validation(exc):
        return jsonify({"error": str(exc), "code": exc.code, "field": exc.field}), 400

    @app.errorhandler(GraphifyError)
    def _handle_graphify(exc):
        return jsonify({"error": str(exc), "code": exc.code}), 500

    @app.errorhandler(404)
    def _handle_404(_exc):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(Exception)
    def _handle_generic(exc):
        logger.exception("Unhandled error: %s", exc)
        return jsonify({"error": "Internal server error"}), 500

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.route("/api/health")
    def health():
        store = _ext("gfx_store")
        stats = store.stats("")
        return jsonify(
            {
                "status": "ok",
                "db": _ext("gfx_db_path"),
                "total_nodes": stats.get("nodes", 0),
            }
        )

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    @app.route("/api/projects")
    def list_projects():
        projects = _ext("gfx_store").list_projects()
        return jsonify(
            [
                {
                    "project_id": p.project_id,
                    "name": p.name,
                    "root_path": p.root_path,
                    "total_files": p.total_files,
                    "total_lines": p.total_lines,
                    "languages": p.languages,
                    "scanned_at": p.scanned_at,
                }
                for p in projects
            ]
        )

    @app.route("/api/projects/<project_id>")
    def get_project(project_id):
        return jsonify(_ext("gfx_query").summary(project_id))

    @app.route("/api/projects/<project_id>/stats")
    def project_stats(project_id):
        return jsonify(_ext("gfx_store").stats(project_id))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    @app.route("/api/search")
    def search():
        q = request.args.get("q", "").strip()
        project_id = request.args.get("project_id", "")
        limit = _safe_int(request.args.get("limit"), 50, hi=500)
        if not q:
            return jsonify({"error": "Missing 'q' parameter"}), 400
        results = _ext("gfx_fts").search(q, project_id=project_id, limit=limit)
        return jsonify(
            [
                {
                    "name": r["node"].name,
                    "type": r["node"].node_type.value,
                    "file": r["node"].file_path,
                    "score": r["score"],
                    "snippet": r["snippet"],
                }
                for r in results
            ]
        )

    @app.route("/api/search/name")
    def search_name():
        name = request.args.get("name", "").strip()
        project_id = request.args.get("project_id", "")
        if not name:
            return jsonify({"error": "Missing 'name' parameter"}), 400
        nodes = _ext("gfx_fts").search_by_name(name, project_id=project_id)
        return jsonify(
            [
                {"id": n.id, "name": n.name, "type": n.node_type.value, "file": n.file_path}
                for n in nodes
            ]
        )

    # ------------------------------------------------------------------
    # Graph queries
    # ------------------------------------------------------------------

    @app.route("/api/files/<path:file_path>")
    def file_structure(file_path):
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").get_file_structure(file_path, project_id))

    @app.route("/api/classes")
    def class_hierarchy():
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").get_class_hierarchy(project_id))

    @app.route("/api/dependencies")
    def dependencies():
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").get_dependencies(project_id))

    @app.route("/api/tests")
    def tests():
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").get_tests(project_id))

    @app.route("/api/hotspots")
    def hotspots():
        project_id = request.args.get("project_id", "")
        top_n = _safe_int(request.args.get("top"), 20, hi=100)
        return jsonify(_ext("gfx_query").complexity_hotspots(project_id, top_n))

    @app.route("/api/languages")
    def languages():
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").language_breakdown(project_id))

    @app.route("/api/subgraph/<node_id>")
    def subgraph(node_id):
        depth = _safe_int(request.args.get("depth"), 3, hi=5)
        return jsonify(_ext("gfx_query").get_subgraph(node_id, max_depth=depth))

    # ------------------------------------------------------------------
    # Intelligence
    # ------------------------------------------------------------------

    @app.route("/api/god-nodes")
    def api_god_nodes():
        project_id = request.args.get("project_id", "")
        top_n = _safe_int(request.args.get("top"), 20, hi=100)
        gods = _ext("gfx_store").god_nodes(project_id, top_n=top_n)
        return jsonify(
            [
                {
                    "name": g["node"].name,
                    "type": g["node"].node_type.value,
                    "file": g["node"].file_path,
                    "degree": g["degree"],
                }
                for g in gods
            ]
        )

    @app.route("/api/explain/<name>")
    def api_explain(name):
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").explain_node(name, project_id=project_id))

    @app.route("/api/path/<start>/<end>")
    def api_path(start, end):
        project_id = request.args.get("project_id", "")
        return jsonify(_ext("gfx_query").find_path(start, end, project_id=project_id))

    @app.route("/api/communities")
    def api_communities():
        project_id = request.args.get("project_id", "")
        communities = _ext("gfx_query").detect_communities(project_id=project_id)
        return jsonify(
            {
                "count": len(communities),
                "communities": {
                    k: {"size": len(v), "nodes": v[:20]}
                    for k, v in sorted(
                        communities.items(),
                        key=lambda x: len(x[1]),
                        reverse=True,
                    )[:50]
                },
            }
        )

    # ------------------------------------------------------------------
    # Metrics & history
    # ------------------------------------------------------------------

    @app.route("/api/metrics/<project_id>")
    def api_metrics(project_id):
        limit = _safe_int(request.args.get("limit"), 20, hi=100)
        return jsonify(
            {
                "history": _ext("gfx_metrics").history(project_id, limit=limit),
                "averages": _ext("gfx_metrics").averages(project_id),
            }
        )

    # ------------------------------------------------------------------
    # Snapshots & diffing
    # ------------------------------------------------------------------

    @app.route("/api/snapshots/<project_id>")
    def api_snapshots(project_id):
        return jsonify(_ext("gfx_differ").list_snapshots(project_id))

    @app.route("/api/snapshots/<project_id>/take", methods=["POST"])
    def api_take_snapshot(project_id):
        label = request.args.get("label", "")
        snap_id = _ext("gfx_differ").take_snapshot(project_id, label=label)
        return jsonify({"snapshot_id": snap_id}), 201

    @app.route("/api/diff/<int:snap_a>/<int:snap_b>")
    def api_diff(snap_a, snap_b):
        diff = _ext("gfx_differ").diff_snapshots(snap_a, snap_b)
        return jsonify(diff.to_dict())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @app.route("/api/export/json")
    def export_json():
        project_id = request.args.get("project_id", "")
        return app.response_class(
            _ext("gfx_exporter").to_json(project_id),
            mimetype="application/json",
        )

    @app.route("/api/export/dot")
    def export_dot():
        project_id = request.args.get("project_id", "")
        return app.response_class(
            _ext("gfx_exporter").to_dot(project_id),
            mimetype="text/plain",
        )

    @app.route("/api/export/markdown")
    def export_markdown():
        project_id = request.args.get("project_id", "")
        return app.response_class(
            _ext("gfx_exporter").to_markdown(project_id),
            mimetype="text/markdown",
        )

    @app.route("/api/export/graphml")
    def export_graphml():
        project_id = request.args.get("project_id", "")
        return app.response_class(
            _ext("gfx_exporter").to_graphml(project_id),
            mimetype="application/xml",
        )

    return app


def run_server(
    db_path: str,
    host: str = "127.0.0.1",
    port: int = 5004,
    allowed_origins: str = "*",
) -> None:
    """Start the API server."""
    app = create_app(db_path, allowed_origins=allowed_origins)
    logger.info("Graphify API server starting on %s:%d", host, port)
    app.run(host=host, port=port)
