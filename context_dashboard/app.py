"""
Context Graph Dashboard — Visualization and management UI.

Serves a web dashboard for exploring and managing context graphs
from both the Orchestrator and Agentic Team systems.

Usage:
    python -m context_dashboard.app
    python context_dashboard/app.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

# Ensure project root is on sys.path for orchestrator/agentic_team imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

app = Flask(__name__)
CORS(app)

VALID_SYSTEMS = ("orchestrator", "agentic_team")
MAX_QUERY_LIMIT = 10000


# ---------------------------------------------------------------------------
# Context system accessors (singletons)
# ---------------------------------------------------------------------------

_orchestrator_ctx = None
_agentic_team_ctx = None


def get_orchestrator_context():
    """Get orchestrator context manager (singleton)."""
    global _orchestrator_ctx
    if _orchestrator_ctx is None:
        try:
            from orchestrator.context import MemoryManager

            _orchestrator_ctx = MemoryManager()
        except Exception:
            pass
    return _orchestrator_ctx


def get_agentic_team_context():
    """Get agentic team context manager (singleton)."""
    global _agentic_team_ctx
    if _agentic_team_ctx is None:
        try:
            from agentic_team.context import MemoryManager

            _agentic_team_ctx = MemoryManager()
        except Exception:
            pass
    return _agentic_team_ctx


def _get_context(system: str):
    """Return the MemoryManager for *system*, or None."""
    if system == "orchestrator":
        return get_orchestrator_context()
    if system == "agentic_team":
        return get_agentic_team_context()
    return None


def _validate_system(system: str):
    """Return an error response if *system* is not valid, else None."""
    if system not in VALID_SYSTEMS:
        return jsonify({"error": f"Invalid system '{system}'. Use one of {VALID_SYSTEMS}"}), 400
    return None


# ---------------------------------------------------------------------------
# Graph data helpers
# ---------------------------------------------------------------------------


def get_graph_data(
    system: str,
    node_types: list[str] | None = None,
    limit: int = 200,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Query nodes and edges from the graph store.

    Args:
        system: 'orchestrator' or 'agentic_team'
        node_types: Optional filter by node types
        limit: Maximum number of nodes to return
        project_id: Optional project scope filter
    """
    manager = _get_context(system)
    if not manager or not hasattr(manager, "graph_store"):
        return {"nodes": [], "edges": []}

    store = manager.graph_store
    try:
        with store._transaction() as cursor:
            conditions: list[str] = []
            params: list[Any] = []

            if node_types:
                placeholders = ",".join("?" * len(node_types))
                conditions.append(f"node_type IN ({placeholders})")
                params.extend(node_types)

            if project_id is not None:
                conditions.append("project_id = ?")
                params.append(project_id)

            where = " AND ".join(conditions) if conditions else "1=1"
            params.append(limit)
            cursor.execute(
                f"SELECT * FROM nodes WHERE {where} ORDER BY created_at DESC LIMIT ?",
                params,
            )

            columns = [d[0] for d in cursor.description]
            nodes = [dict(zip(columns, row)) for row in cursor.fetchall()]

            node_ids = [n["id"] for n in nodes]
            if node_ids:
                ph = ",".join("?" * len(node_ids))
                cursor.execute(
                    f"SELECT * FROM edges WHERE source_id IN ({ph}) OR target_id IN ({ph})",
                    node_ids + node_ids,
                )
                edge_columns = [d[0] for d in cursor.description]
                edges = [dict(zip(edge_columns, row)) for row in cursor.fetchall()]
            else:
                edges = []

        return {"nodes": nodes, "edges": edges}
    except Exception:
        app.logger.exception("Graph query failed")
        return {"nodes": [], "edges": [], "error": "Internal error querying graph data"}


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# Routes — API
# ---------------------------------------------------------------------------


@app.route("/api/graph/<system>")
def api_graph(system: str):
    """Return graph nodes + edges formatted for vis.js."""
    err = _validate_system(system)
    if err:
        return err

    node_types_param = request.args.get("node_types")
    node_types = [t.strip() for t in node_types_param.split(",")] if node_types_param else None
    limit = min(request.args.get("limit", 200, type=int), MAX_QUERY_LIMIT)
    project_id = request.args.get("project_id")

    data = get_graph_data(system, node_types=node_types, limit=limit, project_id=project_id)
    return jsonify(data)


@app.route("/api/projects/<system>")
def api_projects(system: str):
    """List all registered projects in a context system."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager or not hasattr(manager, "graph_store"):
        return jsonify({"projects": []})

    store = manager.graph_store
    try:
        with store._transaction() as cursor:
            cursor.execute(
                "SELECT * FROM nodes WHERE node_type = 'project' ORDER BY created_at DESC"
            )
            columns = [d[0] for d in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        projects = []
        for row in rows:
            extra = json.loads(row.get("extra_data", "{}")) if row.get("extra_data") else {}
            projects.append(
                {
                    "project_id": row.get("project_id", ""),
                    "name": extra.get("project_name", row.get("title", "")),
                    "path": extra.get("project_path", ""),
                    "languages": extra.get("languages", []),
                    "frameworks": extra.get("frameworks", []),
                    "file_count": extra.get("file_count", 0),
                    "last_scanned": extra.get("last_scanned", ""),
                    "created_at": row.get("created_at", ""),
                }
            )
        return jsonify({"projects": projects})
    except Exception:
        app.logger.exception("Projects query failed")
        return jsonify({"projects": [], "error": "Internal error querying graph data"})


@app.route("/api/stats/<system>")
def api_stats(system: str):
    """Return database statistics."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager:
        return jsonify({"available": False, "message": f"{system} context not available"})

    try:
        stats = manager.get_stats() if hasattr(manager, "get_stats") else {}
        graph_stats = manager.graph_store.get_stats() if hasattr(manager, "graph_store") else {}
        return jsonify({"available": True, "stats": stats, "graph_stats": graph_stats})
    except Exception:
        app.logger.exception("Stats query failed")
        return jsonify({"available": False, "error": "Internal server error"})


@app.route("/api/analytics/<system>")
def api_analytics(system: str):
    """Return full analytics report for charts."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager or not hasattr(manager, "graph_store"):
        return jsonify({"available": False, "nodes_by_type": {}, "edges_by_type": {}, "growth": []})

    store = manager.graph_store
    try:
        graph_stats = store.get_stats()

        # Growth over last 30 days
        growth: list[dict[str, Any]] = []
        try:
            with store._transaction() as cursor:
                cursor.execute(
                    "SELECT DATE(created_at) AS day, COUNT(*) AS cnt "
                    "FROM nodes "
                    "WHERE created_at >= DATE('now', '-30 days') "
                    "GROUP BY DATE(created_at) ORDER BY day"
                )
                growth = [{"date": r[0], "count": r[1]} for r in cursor.fetchall()]
        except Exception:
            pass

        # Top mistakes
        top_mistakes: list[dict[str, Any]] = []
        try:
            with store._transaction() as cursor:
                cursor.execute(
                    "SELECT title, importance_score FROM nodes "
                    "WHERE node_type = 'mistake' ORDER BY importance_score DESC LIMIT 10"
                )
                top_mistakes = [
                    {"title": r[0] or "Untitled", "score": r[1]} for r in cursor.fetchall()
                ]
        except Exception:
            pass

        # Top patterns
        top_patterns: list[dict[str, Any]] = []
        try:
            with store._transaction() as cursor:
                cursor.execute(
                    "SELECT title, importance_score FROM nodes "
                    "WHERE node_type = 'pattern' ORDER BY importance_score DESC LIMIT 10"
                )
                top_patterns = [
                    {"title": r[0] or "Untitled", "score": r[1]} for r in cursor.fetchall()
                ]
        except Exception:
            pass

        # Average importance
        avg_importance = 0.0
        try:
            with store._transaction() as cursor:
                cursor.execute("SELECT AVG(importance_score) FROM nodes")
                row = cursor.fetchone()
                avg_importance = round(row[0], 3) if row and row[0] else 0.0
        except Exception:
            pass

        # DB size
        db_size_bytes = 0
        try:
            db_path = Path(store.db_path) if hasattr(store, "db_path") else None
            if db_path and db_path.exists():
                db_size_bytes = db_path.stat().st_size
        except Exception:
            pass

        return jsonify(
            {
                "available": True,
                "nodes_by_type": graph_stats.get("nodes_by_type", {}),
                "edges_by_type": graph_stats.get("edges_by_type", {}),
                "total_nodes": graph_stats.get("total_nodes", 0),
                "total_edges": graph_stats.get("total_edges", 0),
                "avg_importance": avg_importance,
                "db_size_bytes": db_size_bytes,
                "growth": growth,
                "top_mistakes": top_mistakes,
                "top_patterns": top_patterns,
            }
        )
    except Exception:
        app.logger.exception("Analytics query failed")
        return jsonify({"available": False, "error": "Analytics query failed"})


@app.route("/api/search/<system>")
def api_search(system: str):
    """Search context nodes."""
    err = _validate_system(system)
    if err:
        return err

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": [], "error": "Missing query parameter ?q="})

    node_types_param = request.args.get("node_types")
    node_types = [t.strip() for t in node_types_param.split(",")] if node_types_param else None
    limit = min(request.args.get("limit", 20, type=int), MAX_QUERY_LIMIT)

    manager = _get_context(system)
    if not manager:
        return jsonify({"results": [], "error": f"{system} context not available"})

    try:
        if hasattr(manager, "search"):
            results = manager.search(query, limit=limit, node_types=node_types)
            items = []
            for r in results:
                node = r.node if hasattr(r, "node") else r
                items.append(
                    {
                        "id": node.id if hasattr(node, "id") else str(node),
                        "node_type": node.node_type if hasattr(node, "node_type") else "unknown",
                        "title": node.title if hasattr(node, "title") else "",
                        "content": (node.content if hasattr(node, "content") else "")[:500],
                        "importance_score": (
                            node.importance_score if hasattr(node, "importance_score") else 0
                        ),
                        "created_at": str(node.created_at) if hasattr(node, "created_at") else "",
                        "tags": node.tags if hasattr(node, "tags") else [],
                        "score": r.score if hasattr(r, "score") else 0,
                    }
                )
            return jsonify({"results": items})
        if hasattr(manager, "graph_store"):
            results = manager.graph_store.full_text_search(query, limit=limit)
            items = []
            for node, score in results:
                if node_types and node.node_type not in node_types:
                    continue
                items.append(
                    {
                        "id": node.id,
                        "node_type": node.node_type,
                        "title": node.title,
                        "content": (node.content or "")[:500],
                        "importance_score": node.importance_score,
                        "created_at": str(node.created_at),
                        "tags": node.tags if hasattr(node, "tags") else [],
                        "score": score,
                    }
                )
            return jsonify({"results": items})
        return jsonify({"results": [], "error": "Search not available"})
    except Exception:
        app.logger.exception("Search query failed")
        return jsonify({"results": [], "error": "Search query failed"})


@app.route("/api/node/<system>/<node_id>")
def api_node(system: str, node_id: str):
    """Get full detail for a single node."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager or not hasattr(manager, "graph_store"):
        return jsonify({"error": "Context not available"}), 404

    try:
        node = manager.graph_store.get_node(node_id)
        if not node:
            return jsonify({"error": "Node not found"}), 404

        node_dict = {
            "id": node.id,
            "node_type": (
                node.node_type if isinstance(node.node_type, str) else node.node_type.value
            ),
            "title": node.title,
            "content": node.content,
            "metadata": node.metadata if hasattr(node, "metadata") else {},
            "tags": node.tags if hasattr(node, "tags") else [],
            "created_at": str(node.created_at),
            "updated_at": str(node.updated_at) if hasattr(node, "updated_at") else "",
            "importance_score": node.importance_score if hasattr(node, "importance_score") else 1.0,
        }

        # Get connected edges
        edges_from = manager.graph_store.get_edges_from(node_id)
        edges_to = manager.graph_store.get_edges_to(node_id)
        node_dict["edges_from"] = [
            {
                "id": e.id,
                "target_id": e.target_id,
                "edge_type": e.edge_type if isinstance(e.edge_type, str) else e.edge_type.value,
                "weight": e.weight,
            }
            for e in edges_from
        ]
        node_dict["edges_to"] = [
            {
                "id": e.id,
                "source_id": e.source_id,
                "edge_type": e.edge_type if isinstance(e.edge_type, str) else e.edge_type.value,
                "weight": e.weight,
            }
            for e in edges_to
        ]

        return jsonify(node_dict)
    except Exception:
        app.logger.exception("Node operation failed")
        return jsonify({"error": "Node operation failed"}), 500


@app.route("/api/prune/<system>", methods=["POST"])
def api_prune(system: str):
    """Trigger graph pruning."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager:
        return jsonify({"error": "Context not available"}), 404

    body = request.get_json(silent=True) or {}
    strategy = body.get("strategy", "age")

    try:
        if system == "agentic_team":
            from agentic_team.context.ops.pruning import ContextPruner as ATContextPruner

            pruner = ATContextPruner(manager.graph_store)
        else:
            from orchestrator.context.pruning import ContextPruner

            pruner = ContextPruner(manager.graph_store)

        if strategy == "age":
            max_age_days = body.get("max_age_days", 90)
            result = pruner.prune_by_age(max_age_days=max_age_days)
        elif strategy == "duplicates":
            if system == "agentic_team":
                result = pruner.prune_duplicates()  # type: ignore[call-arg]
            else:
                threshold = body.get("similarity_threshold", 0.95)
                result = pruner.prune_duplicates(similarity_threshold=threshold)  # type: ignore[call-arg]
        elif strategy == "low_importance":
            threshold = body.get("importance_threshold", 0.3)
            min_age = body.get("min_age_days", 7)
            if system == "agentic_team":
                result = pruner.prune_low_importance(  # type: ignore[call-arg]
                    threshold=threshold, min_age_days=min_age
                )
            else:
                result = pruner.prune_low_importance(
                    importance_threshold=threshold, min_age_days=min_age  # type: ignore[call-arg]
                )
        elif strategy == "all":
            result = pruner.prune_all(
                age_days=body.get("max_age_days", 90),
                importance_threshold=body.get("importance_threshold", 0.2),
                remove_duplicates=body.get("remove_duplicates", True),
            )
        else:
            return jsonify({"error": f"Unknown strategy: {strategy}"}), 400

        return jsonify({"success": True, "result": result})
    except ImportError:
        return jsonify({"error": "Pruning module not available"}), 500
    except Exception:
        app.logger.exception("Prune operation failed")
        return jsonify({"error": "Node operation failed"}), 500


@app.route("/api/export/<system>")
def api_export(system: str):
    """Export the context graph as a downloadable JSON file."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager or not hasattr(manager, "graph_store"):
        return jsonify({"error": "Context not available"}), 404

    try:
        # Build export dict in memory
        data = get_graph_data(system, limit=100000)
        export_payload = {
            "version": "1.0",
            "system": system,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "stats": {"nodes": len(data["nodes"]), "edges": len(data["edges"])},
            "nodes": data["nodes"],
            "edges": data["edges"],
        }

        buf = io.BytesIO()
        buf.write(json.dumps(export_payload, indent=2, default=str).encode("utf-8"))
        buf.seek(0)
        filename = f"context_{system}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        return send_file(
            buf, mimetype="application/json", as_attachment=True, download_name=filename
        )
    except ImportError:
        # Fall back to raw export
        data = get_graph_data(system, limit=100000)
        export_payload = {
            "version": "1.0",
            "system": system,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "stats": {"nodes": len(data["nodes"]), "edges": len(data["edges"])},
            "nodes": data["nodes"],
            "edges": data["edges"],
        }
        buf = io.BytesIO()
        buf.write(json.dumps(export_payload, indent=2, default=str).encode("utf-8"))
        buf.seek(0)
        filename = f"context_{system}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        return send_file(
            buf, mimetype="application/json", as_attachment=True, download_name=filename
        )
    except Exception:
        app.logger.exception("Export failed")
        return jsonify({"error": "Export failed"}), 500


@app.route("/api/import/<system>", methods=["POST"])
def api_import(system: str):
    """Import context graph from uploaded JSON."""
    err = _validate_system(system)
    if err:
        return err

    manager = _get_context(system)
    if not manager or not hasattr(manager, "graph_store"):
        return jsonify({"error": "Context not available"}), 404

    if "file" not in request.files:
        return (
            jsonify({"error": "No file uploaded. Use multipart/form-data with field 'file'."}),
            400,
        )

    file = request.files["file"]
    try:
        payload = json.loads(file.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return jsonify({"error": f"Invalid JSON: {exc}"}), 400

    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    imported_nodes = 0
    imported_edges = 0

    store = manager.graph_store
    try:
        with store._transaction() as cursor:
            for n in nodes:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO nodes "
                        "(id, node_type, title, content, metadata, tags, "
                        "created_at, updated_at, importance_score, extra_data) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            n.get("id", str(uuid.uuid4())),
                            n.get("node_type", "unknown"),
                            n.get("title", ""),
                            n.get("content", ""),
                            (
                                json.dumps(n.get("metadata", {}))
                                if isinstance(n.get("metadata"), dict)
                                else n.get("metadata", "{}")
                            ),
                            (
                                json.dumps(n.get("tags", []))
                                if isinstance(n.get("tags"), list)
                                else n.get("tags", "[]")
                            ),
                            n.get("created_at", datetime.now(timezone.utc).isoformat()),
                            n.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            n.get("importance_score", 1.0),
                            (
                                json.dumps(n.get("extra_data", {}))
                                if isinstance(n.get("extra_data"), dict)
                                else n.get("extra_data", "{}")
                            ),
                        ),
                    )
                    imported_nodes += cursor.rowcount
                except Exception:
                    pass

            for e in edges:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO edges "
                        "(id, source_id, target_id, edge_type, weight, metadata, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            e.get("id", str(uuid.uuid4())),
                            e.get("source_id"),
                            e.get("target_id"),
                            e.get("edge_type", "related_to"),
                            e.get("weight", 1.0),
                            (
                                json.dumps(e.get("metadata", {}))
                                if isinstance(e.get("metadata"), dict)
                                else e.get("metadata", "{}")
                            ),
                            e.get("created_at", datetime.now(timezone.utc).isoformat()),
                        ),
                    )
                    imported_edges += cursor.rowcount
                except Exception:
                    pass

        return jsonify(
            {"success": True, "imported_nodes": imported_nodes, "imported_edges": imported_edges}
        )
    except Exception:
        app.logger.exception("Import failed")
        return jsonify({"error": "Node operation failed"}), 500


@app.route("/health")
def health():
    """Health check endpoint."""
    orchestrator_ok = get_orchestrator_context() is not None
    agentic_ok = get_agentic_team_context() is not None
    return jsonify(
        {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "systems": {
                "orchestrator": orchestrator_ok,
                "agentic_team": agentic_ok,
            },
        }
    )


@app.route("/api/combined/stats")
def api_combined_stats():
    """Return aggregated statistics from BOTH context systems."""
    systems: dict[str, Any] = {}
    totals: dict[str, Any] = {"nodes": 0, "edges": 0, "nodes_by_type": {}, "edges_by_type": {}}
    for system in VALID_SYSTEMS:
        mgr = _get_context(system)
        if mgr:
            try:
                stats = mgr.get_stats() if hasattr(mgr, "get_stats") else {}
                graph_stats = mgr.graph_store.get_stats() if hasattr(mgr, "graph_store") else {}
                systems[system] = {
                    "available": True,
                    "stats": stats,
                    "graph_stats": graph_stats,
                }
                totals["nodes"] += graph_stats.get("total_nodes", 0)
                totals["edges"] += graph_stats.get("total_edges", 0)
                for ntype, cnt in graph_stats.get("nodes_by_type", {}).items():
                    totals["nodes_by_type"][ntype] = totals["nodes_by_type"].get(ntype, 0) + cnt
                for etype, cnt in graph_stats.get("edges_by_type", {}).items():
                    totals["edges_by_type"][etype] = totals["edges_by_type"].get(etype, 0) + cnt
            except Exception:
                app.logger.exception("Combined stats query failed for %s", system)
                systems[system] = {"available": False, "error": "Internal server error"}
        else:
            systems[system] = {"available": False}
    return jsonify(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "systems": systems,
            "totals": totals,
        }
    )


@app.route("/api/combined/graph")
def api_combined_graph():
    """Return graph data from BOTH systems, prefixed to avoid ID collisions."""
    limit = min(request.args.get("limit", 150, type=int), MAX_QUERY_LIMIT)
    combined_nodes = []
    combined_edges = []
    for system in VALID_SYSTEMS:
        data = get_graph_data(system, limit=limit)
        prefix = "orch_" if system == "orchestrator" else "at_"
        for node in data.get("nodes", []):
            node["id"] = prefix + str(node["id"])
            node["_system"] = system
            combined_nodes.append(node)
        for edge in data.get("edges", []):
            edge["source_id"] = prefix + str(edge["source_id"])
            edge["target_id"] = prefix + str(edge["target_id"])
            edge["_system"] = system
            combined_edges.append(edge)
    return jsonify({"nodes": combined_nodes, "edges": combined_edges})


# ---------------------------------------------------------------------------
# Auto-seed on first run
# ---------------------------------------------------------------------------


def _auto_seed_if_empty():
    """Seed context graphs with sample data if both are empty."""
    try:
        orc = get_orchestrator_context()
        at = get_agentic_team_context()
        orc_empty = True
        at_empty = True
        if orc and hasattr(orc, "graph_store"):
            stats = orc.graph_store.get_stats()
            orc_empty = stats.get("total_nodes", 0) == 0
        if at and hasattr(at, "graph_store"):
            stats = at.graph_store.get_stats()
            at_empty = stats.get("total_nodes", 0) == 0

        if orc_empty or at_empty:
            seed_script = (
                Path(__file__).resolve().parent.parent / "scripts" / "seed_context_graphs.py"
            )
            if seed_script.exists():
                import subprocess

                args = [sys.executable, str(seed_script)]
                if orc_empty and not at_empty:
                    args += ["--system", "orchestrator"]
                elif at_empty and not orc_empty:
                    args += ["--system", "agentic_team"]
                result = subprocess.run(
                    args, capture_output=True, timeout=30, text=True, check=False
                )
                if result.returncode != 0:
                    app.logger.warning("Auto-seed failed: %s", result.stderr[:500])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _auto_seed_if_empty()
    app.run(
        host=os.environ.get("DASHBOARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("DASHBOARD_PORT", "5003")),
        debug=os.environ.get("DASHBOARD_DEBUG", "").lower() == "true",
    )
