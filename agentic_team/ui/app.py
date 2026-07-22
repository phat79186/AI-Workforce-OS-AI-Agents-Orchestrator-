"""
Standalone Agentic Team UI backend.

This app is intentionally separate from the orchestrator UI backend (ui/app.py).
It serves a dedicated interface for the AgenticTeamEngine only.
"""

import logging
import os
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

import httpx
import yaml
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room

# Add project root to import path.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agentic_team import AgenticTeamEngine  # noqa: E402  # pylint: disable=wrong-import-position

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY_AGENTIC", os.urandom(32).hex())
CORS(app, origins=os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(","))
socketio = SocketIO(
    app,
    cors_allowed_origins=os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(","),
    async_mode="threading",
    allow_upgrades=False,  # threading mode only supports polling, prevent WebSocket 500
)
FRONTEND_PUBLIC_DIR = Path(__file__).parent / "frontend" / "public"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentic_ui")

engine: Optional[Any] = None
session_lock = Lock()
DEFAULT_CLIENT_ID = "default"
client_sessions: Dict[str, Dict[str, Any]] = {}
sid_to_client: Dict[str, str] = {}
MAX_SESSION_LOGS = 500
LOCAL_BACKEND_DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai-compatible": "http://localhost:8080",
}


def _normalize_client_id(raw: Optional[str]) -> str:
    if not isinstance(raw, str):
        return DEFAULT_CLIENT_ID
    value = raw.strip()
    if not value:
        return DEFAULT_CLIENT_ID
    return value[:128]


def _get_client_id_from_request(payload: Optional[Dict[str, Any]] = None) -> str:
    payload_client_id = payload.get("client_id") if isinstance(payload, dict) else None
    header_client_id = request.headers.get("X-Client-Id")
    query_client_id = request.args.get("client_id")
    return _normalize_client_id(payload_client_id or query_client_id or header_client_id)


def _new_session_state() -> Dict[str, Any]:
    return {
        "task": None,
        "status": "idle",
        "cancelled": False,
        "results": None,
        "team_turns": [],
        "team_communications": [],
        "team_config": None,
        "conversation_history": [],
        "last_task": None,
        "last_output": None,
        "logs": [],
        "started_at": None,
        "updated_at": datetime.now().isoformat(),
    }


def _get_session_snapshot(client_id: str) -> Dict[str, Any]:
    normalized = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.get(normalized)
        if session is None:
            session = _new_session_state()
            client_sessions[normalized] = session
        return deepcopy(session)


def _record_log(client_id: str, message: str, level: str = "info") -> None:
    if not isinstance(message, str) or not message.strip():
        return
    normalized = _normalize_client_id(client_id)
    entry = {
        "message": message.strip(),
        "level": str(level or "info").lower(),
        "timestamp": datetime.now().isoformat(),
    }
    with session_lock:
        session = client_sessions.setdefault(normalized, _new_session_state())
        logs = session.setdefault("logs", [])
        logs.append(entry)
        if len(logs) > MAX_SESSION_LOGS:
            del logs[: len(logs) - MAX_SESSION_LOGS]
        session["updated_at"] = datetime.now().isoformat()


def _emit_log(client_id: str, message: str, level: str = "info") -> None:
    payload = {
        "message": message.strip(),
        "level": str(level or "info").lower(),
        "timestamp": datetime.now().isoformat(),
    }
    _record_log(client_id, payload["message"], payload["level"])
    socketio.emit("progress_log", payload, namespace="/", to=_normalize_client_id(client_id))


def _record_team_turn(client_id: str, payload: Dict[str, Any]) -> None:
    normalized = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.setdefault(normalized, _new_session_state())
        turns = session.setdefault("team_turns", [])
        turns.append(payload)
        session["updated_at"] = datetime.now().isoformat()


def _record_team_communication(client_id: str, payload: Dict[str, Any]) -> None:
    normalized = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.setdefault(normalized, _new_session_state())
        comms = session.setdefault("team_communications", [])
        comms.append(payload)
        session["updated_at"] = datetime.now().isoformat()


def _emit_team_turn(client_id: str, payload: Dict[str, Any]) -> None:
    if "timestamp" not in payload:
        payload = {**payload, "timestamp": datetime.now().isoformat()}
    _record_team_turn(client_id, payload)
    socketio.emit("team_turn", payload, namespace="/", to=_normalize_client_id(client_id))
    communication_payload = {
        "event": "team_communication",
        "timestamp": payload.get("timestamp"),
        "turn": payload.get("turn"),
        "action": payload.get("action"),
        "from_role": payload.get("from_role"),
        "to_role": payload.get("to_role"),
        "from_agent": payload.get("from_agent") or payload.get("agent"),
        "to_agent": payload.get("to_agent"),
        "message": payload.get("message", ""),
        "success": payload.get("success"),
    }
    _record_team_communication(client_id, communication_payload)
    socketio.emit(
        "team_communication",
        communication_payload,
        namespace="/",
        to=_normalize_client_id(client_id),
    )
    route = (
        f"Turn {payload.get('turn', '?')}: "
        f"{payload.get('from_role', '?')} ({communication_payload.get('from_agent') or 'unknown'}) "
        f"-> {payload.get('to_role', '?')} ({communication_payload.get('to_agent') or 'unknown'}) "
        f"[{payload.get('action', 'message')}]"
    )
    _emit_log(client_id, route, "info")


def _config_path() -> Path:
    override = os.getenv("AGENTIC_TEAM_CONFIG_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).parent.parent / "config" / "agents.yaml"


def _init_engine() -> None:
    global engine
    engine = AgenticTeamEngine(config_path=str(_config_path()))


def _validate_config_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    config_obj = payload.get("config")
    content = payload.get("content")
    if isinstance(config_obj, dict):
        parsed = config_obj
    elif isinstance(content, str) and content.strip():
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML: {exc}") from exc
    else:
        raise ValueError("Provide either 'config' object or non-empty 'content' YAML")

    if not isinstance(parsed, dict):
        raise ValueError("Top-level YAML must be a mapping/object")
    for section in ["agents", "workflows", "settings"]:
        if section not in parsed:
            raise ValueError(f"Missing required section: {section}")
        if not isinstance(parsed.get(section), dict):
            raise ValueError(f"Section '{section}' must be a mapping/object")
    team_cfg = parsed.get("agentic_team")
    if team_cfg is not None and not isinstance(team_cfg, dict):
        raise ValueError("'agentic_team' must be a mapping/object when provided")
    return parsed


def _dump_config_yaml(config_obj: Dict[str, Any]) -> str:
    return yaml.safe_dump(
        config_obj,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=False,
    )


def _canonical_local_backend_type(agent_type: Any) -> Optional[str]:
    """Map configured agent type to a local backend family."""
    normalized = str(agent_type or "").strip().lower()
    if normalized == "ollama":
        return "ollama"
    if normalized in {"llamacpp", "localai", "text-generation-webui", "openai-compatible"}:
        return "openai-compatible"
    return None


def _probe_ollama_backend(endpoint: str) -> Dict[str, Any]:
    """Probe Ollama endpoint and return model metadata."""
    try:
        response = httpx.get(f"{endpoint}/api/tags", timeout=3)
        response.raise_for_status()
        raw_models = response.json().get("models", [])
        models = []
        models_detailed = []
        for item in raw_models:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            models.append(name)
            models_detailed.append(
                {
                    "name": name,
                    "size_bytes": item.get("size"),
                    "modified_at": item.get("modified_at"),
                    "digest": item.get("digest"),
                }
            )
        return {
            "online": True,
            "models": models,
            "models_detailed": models_detailed,
            "error": None,
        }
    except Exception as exc:  # nosec B112 - backend probe should fail closed
        return {"online": False, "models": [], "models_detailed": [], "error": str(exc)}


def _probe_openai_compatible_backend(endpoint: str) -> Dict[str, Any]:
    """Probe OpenAI-compatible endpoint (llama.cpp/LocalAI/text-generation-webui)."""
    online = False
    health_error: Optional[str] = None

    for url in [f"{endpoint}/health", f"{endpoint}/v1/models", endpoint]:
        try:
            resp = httpx.get(url, timeout=2)
            if resp.status_code < 500:
                online = True
                break
        except Exception as exc:  # nosec B112 - backend probe should fail closed
            health_error = str(exc)

    if not online:
        return {
            "online": False,
            "models": [],
            "models_detailed": [],
            "error": health_error or "Endpoint is unreachable",
        }

    try:
        resp = httpx.get(f"{endpoint}/v1/models", timeout=3)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        models = []
        models_detailed = []
        for item in data:
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            models.append(model_id)
            models_detailed.append(
                {
                    "id": model_id,
                    "owned_by": item.get("owned_by"),
                    "created": item.get("created"),
                }
            )
        return {
            "online": True,
            "models": models,
            "models_detailed": models_detailed,
            "error": None,
        }
    except Exception as exc:  # nosec B112 - model listing may be optional
        return {
            "online": True,
            "models": [],
            "models_detailed": [],
            "error": f"Model listing unavailable: {exc}",
        }


def _probe_local_backend(backend_type: str, endpoint: str) -> Dict[str, Any]:
    """Probe a local backend and return normalized status payload."""
    if backend_type == "ollama":
        return _probe_ollama_backend(endpoint)
    return _probe_openai_compatible_backend(endpoint)


def _team_validation_payload() -> Dict[str, Any]:
    """Compute team-config validity against currently available agents."""
    if not engine:
        _init_engine()

    if hasattr(engine, "validate_team_bindings"):
        payload = engine.validate_team_bindings()
        if isinstance(payload, dict):
            return payload

    team_cfg = engine.get_team_config()
    available = sorted(engine.get_available_agents())
    available_set = set(available)
    missing_roles = []

    for role_name, role_spec in (team_cfg.get("roles") or {}).items():
        agent_name = role_spec.get("agent")
        if not isinstance(agent_name, str) or not agent_name or agent_name not in available_set:
            missing_roles.append({"role": role_name, "agent": agent_name})

    return {
        "valid": len(missing_roles) == 0,
        "available_agents": available,
        "missing_roles": missing_roles,
        "reason": (
            "no_available_agents"
            if not available
            else ("invalid_mappings" if missing_roles else "")
        ),
    }


def _serve_frontend_public_asset(filename: str, mimetype: Optional[str] = None):
    """Serve shared favicon/PWA assets from frontend public directory."""
    return send_from_directory(str(FRONTEND_PUBLIC_DIR), filename, mimetype=mimetype)


@app.route("/favicon.ico")
def favicon():
    """Serve favicon.ico for browser tab icon support."""
    return _serve_frontend_public_asset("favicon.ico", "image/x-icon")


@app.route("/favicon-16x16.png")
def favicon_16():
    """Serve 16x16 favicon asset."""
    return _serve_frontend_public_asset("favicon-16x16.png", "image/png")


@app.route("/favicon-32x32.png")
def favicon_32():
    """Serve 32x32 favicon asset."""
    return _serve_frontend_public_asset("favicon-32x32.png", "image/png")


@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    """Serve Apple touch icon asset."""
    return _serve_frontend_public_asset("apple-touch-icon.png", "image/png")


@app.route("/android-chrome-192x192.png")
def android_chrome_192():
    """Serve Android 192x192 icon asset."""
    return _serve_frontend_public_asset("android-chrome-192x192.png", "image/png")


@app.route("/android-chrome-512x512.png")
def android_chrome_512():
    """Serve Android 512x512 icon asset."""
    return _serve_frontend_public_asset("android-chrome-512x512.png", "image/png")


@app.route("/agentic.webmanifest")
def agentic_webmanifest():
    """Serve agentic-team web manifest."""
    return send_from_directory(
        app.static_folder, "agentic.webmanifest", mimetype="application/manifest+json"
    )


@app.route("/")
def index():
    """Serve the Vue frontend build."""
    dist_index = Path(__file__).parent / "frontend" / "dist" / "index.html"
    if dist_index.exists():
        return dist_index.read_text(encoding="utf-8")
    return render_template("agentic_team.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serve Vue frontend built assets."""
    dist_dir = Path(__file__).parent / "frontend" / "dist" / "assets"
    return send_from_directory(str(dist_dir), filename)


@app.route("/health", methods=["GET"])
def health():
    """Health probe endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200


@app.route("/ready", methods=["GET"])
def ready():
    """Readiness probe validating that at least one agent is executable."""
    try:
        if not engine:
            _init_engine()
        available_agents = engine.get_available_agents()
        if not available_agents:
            return (
                jsonify(
                    {
                        "status": "not ready",
                        "reason": "no available agents for agentic team",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                503,
            )
        return (
            jsonify(
                {
                    "status": "ready",
                    "agents_count": len(available_agents),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )
    except Exception as exc:
        return (
            jsonify(
                {"status": "not ready", "reason": str(exc), "timestamp": datetime.now().isoformat()}
            ),
            503,
        )


@app.route("/api/team/config", methods=["GET"])
def get_team_config():
    """Return effective team config, validation payload, and runtime status."""
    if not engine:
        _init_engine()
    runtime_status = engine.get_runtime_status() if hasattr(engine, "get_runtime_status") else {}
    return jsonify(
        {
            "team": engine.get_team_config(),
            "agents": engine.get_available_agents(),
            "validation": _team_validation_payload(),
            "runtime_status": runtime_status,
        }
    )


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return raw and parsed YAML configuration currently in use."""
    path = _config_path()
    if not path.exists():
        return jsonify({"error": f"Config file not found: {path}"}), 404
    content = path.read_text(encoding="utf-8")
    parsed: Dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(content)
        if isinstance(loaded, dict):
            parsed = loaded
    except yaml.YAMLError:
        parsed = {}
    return jsonify(
        {
            "path": str(path),
            "content": content,
            "parsed": parsed,
            "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        }
    )


@app.route("/api/config", methods=["PUT"])
def put_config():
    """Update YAML config, reload engine, and return fresh validation state."""
    data = request.get_json(silent=True) or {}
    try:
        parsed = _validate_config_payload(data)
        serialized = _dump_config_yaml(parsed)
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
        _init_engine()
        validation = _team_validation_payload()
        return jsonify(
            {
                "message": "Configuration updated and agentic team engine reloaded",
                "path": str(path),
                "content": serialized,
                "parsed": parsed,
                "validation": validation,
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.error("Config update failed: %s", exc, exc_info=True)
        return jsonify({"error": f"Failed to update config: {exc}"}), 500


@app.route("/api/execute", methods=["POST"])
def execute():
    """Start async agentic-team execution for a task."""
    data = request.get_json(silent=True) or {}
    task = data.get("task")
    try:
        max_turns = int(data.get("max_turns", 12))
    except (TypeError, ValueError):
        max_turns = 12
    is_followup = bool(data.get("is_followup", False))
    client_id = _get_client_id_from_request(data)

    if not task or not isinstance(task, str) or not task.strip():
        return jsonify({"error": "Task is required and must be a non-empty string"}), 400
    task = task.strip()
    if len(task) > 50000:
        return jsonify({"error": "Task exceeds maximum length of 50000 characters"}), 400

    if not engine:
        _init_engine()

    validation = _team_validation_payload()
    if not validation.get("available_agents"):
        return (
            jsonify(
                {
                    "error": (
                        "No available agents detected. "
                        "Enable/install at least one agent before running."
                    ),
                    "validation": validation,
                }
            ),
            400,
        )
    if not validation.get("valid", False):
        missing = validation.get("missing_roles", [])
        missing_text = ", ".join(f"{item.get('role')}:{item.get('agent')}" for item in missing)
        return (
            jsonify(
                {
                    "error": (
                        "Team configuration is invalid. Roles mapped to unavailable agents: "
                        f"{missing_text}"
                    ),
                    "validation": validation,
                }
            ),
            400,
        )

    actual_task = task
    session_snapshot = _get_session_snapshot(client_id)
    if is_followup and session_snapshot.get("last_task"):
        previous_task = session_snapshot["last_task"]
        previous_output = session_snapshot.get("last_output", "")
        actual_task = (
            f"Previous task: {previous_task}\n"
            f"Previous result: {previous_output}\n\n"
            f"Follow-up: {task}"
        )

    with session_lock:
        session = client_sessions.setdefault(client_id, _new_session_state())
        session["task"] = task
        session["status"] = "running"
        session["results"] = None
        session["team_turns"] = []
        session["team_communications"] = []
        session["team_config"] = None
        session["logs"] = []
        session["started_at"] = datetime.now().isoformat()
        session["updated_at"] = datetime.now().isoformat()
        session["conversation_history"].append(
            {
                "role": "user",
                "content": task,
                "is_followup": is_followup,
                "timestamp": datetime.now().isoformat(),
            }
        )

    socketio.start_background_task(_execute_async, client_id, actual_task, max_turns)
    return jsonify({"message": "Task started", "client_id": client_id})


def _execute_async(client_id: str, task: str, max_turns: int):
    """Background worker that runs the team and streams events to the client room."""
    normalized = _normalize_client_id(client_id)
    try:
        socketio.emit(
            "task_started",
            {"task": task, "max_turns": max_turns, "engine": "agentic_team"},
            namespace="/",
            to=normalized,
        )
        _emit_log(normalized, f"Starting agentic team execution (max turns: {max_turns})", "info")

        result = engine.execute_task(
            task=task,
            max_turns=max_turns,
            turn_callback=lambda step: _emit_team_turn(
                normalized, {**step, "event": "team_turn", "engine": "agentic_team"}
            ),
        )

        final_output = result.get("final_output", "")
        iterations = result.get("iterations", [])
        turns = iterations[0].get("steps", []) if iterations else []

        with session_lock:
            session = client_sessions.setdefault(normalized, _new_session_state())
            session["results"] = result
            session["team_turns"] = turns
            if not session.get("team_communications"):
                session["team_communications"] = [
                    {
                        "event": "team_communication",
                        "timestamp": step.get("timestamp"),
                        "turn": step.get("turn"),
                        "action": step.get("action"),
                        "from_role": step.get("from_role"),
                        "to_role": step.get("to_role"),
                        "from_agent": step.get("from_agent") or step.get("agent"),
                        "to_agent": step.get("to_agent"),
                        "message": step.get("message", ""),
                        "success": step.get("success"),
                    }
                    for step in turns
                ]
            session["team_config"] = result.get("team")
            session["status"] = "completed" if result.get("success") else "failed"
            session["last_task"] = session.get("task")
            session["last_output"] = final_output
            session["updated_at"] = datetime.now().isoformat()
            session["conversation_history"].append(
                {
                    "role": "assistant",
                    "content": final_output,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        _emit_log(normalized, "Agentic team execution completed", "success")
        socketio.emit(
            "task_completed",
            {
                "success": result.get("success"),
                "output": final_output,
                "iterations": iterations,
                "team_turns": turns,
                "team_communications": _get_session_snapshot(normalized).get(
                    "team_communications", []
                ),
                "team_config": result.get("team"),
            },
            namespace="/",
            to=normalized,
        )
    except Exception as exc:
        logger.error("Agentic execution failed: %s", exc, exc_info=True)
        with session_lock:
            session = client_sessions.setdefault(normalized, _new_session_state())
            session["status"] = "error"
            session["updated_at"] = datetime.now().isoformat()
        _emit_log(normalized, f"Task error: {exc}", "error")
        socketio.emit("task_error", {"error": str(exc)}, namespace="/", to=normalized)


@app.route("/api/status", methods=["GET"])
def status():
    """Return per-client execution/session state snapshot."""
    client_id = _get_client_id_from_request()
    snapshot = _get_session_snapshot(client_id)
    snapshot["client_id"] = client_id
    return jsonify(snapshot)


@app.route("/api/conversation/clear", methods=["POST"])
def clear_conversation():
    """Reset per-client conversation/session state."""
    data = request.get_json(silent=True) or {}
    client_id = _get_client_id_from_request(data)
    with session_lock:
        client_sessions[client_id] = _new_session_state()
    return jsonify({"message": "Conversation cleared", "client_id": client_id})


@app.route("/api/cancel", methods=["POST"])
def cancel_execution():
    """Cancel a running agentic team task."""
    data = request.get_json(silent=True) or {}
    client_id = _get_client_id_from_request(data)
    normalized = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.get(normalized)
        if session and session.get("status") == "running":
            session["cancelled"] = True
            session["status"] = "cancelled"
            session["updated_at"] = datetime.now().isoformat()
    _emit_log(normalized, "Execution cancelled by user", "warn")
    socketio.emit("task_cancelled", {"client_id": normalized}, namespace="/", to=normalized)
    return jsonify({"message": "Cancellation requested", "client_id": normalized})


@app.route("/api/files", methods=["GET"])
@app.route("/api/files/<path:filename>", methods=["GET"])
def get_file(filename=None):
    """Get file content."""
    if filename is None:
        filename = request.args.get("path", "")
    if not filename:
        return jsonify({"error": "No file path provided"}), 400

    project_root = Path(__file__).resolve().parent.parent.parent
    file_path = Path(filename)
    if file_path.is_absolute():
        file_path = file_path.resolve()
    else:
        for base in [project_root / "output", project_root / "workspace", project_root]:
            candidate = (base / filename).resolve()
            if candidate.exists():
                file_path = candidate
                break
        else:
            file_path = (project_root / "output" / filename).resolve()

    if not str(file_path).startswith(str(project_root)):
        return jsonify({"error": "Access denied"}), 403
    if not file_path.exists():
        return jsonify({"error": f"File not found: {filename}"}), 404
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "Binary file"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".html": "html",
    }
    lang = ext_map.get(file_path.suffix.lower(), "plaintext")
    return jsonify(
        {"filename": str(file_path.relative_to(project_root)), "content": content, "language": lang}
    )


@app.route("/api/files/list", methods=["GET"])
def list_workspace_files():
    """List all files in output/ and workspace/ directories."""
    project_root = Path(__file__).resolve().parent.parent.parent
    dirs_to_scan = [
        project_root / "output",
        project_root / "workspace",
    ]

    all_files = []
    skip_patterns = {"__pycache__", ".pyc", ".git", "node_modules", ".DS_Store", ".coverage"}

    for scan_dir in dirs_to_scan:
        if not scan_dir.exists():
            continue
        for file_path in scan_dir.rglob("*"):
            if file_path.is_file():
                if any(skip in str(file_path) for skip in skip_patterns):
                    continue
                try:
                    rel_path = str(file_path.relative_to(project_root))
                    all_files.append(rel_path)
                except ValueError:
                    pass

    return jsonify({"files": sorted(all_files)})


@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Return list of available agents in the team."""
    # Standard agentic team roles
    agents = [
        {"name": "Project Manager", "role": "project_manager", "available": True},
        {"name": "Architect", "role": "architect", "available": True},
        {"name": "Developer", "role": "developer", "available": True},
        {"name": "QA Engineer", "role": "qa", "available": True},
        {"name": "DevOps", "role": "devops", "available": True},
    ]
    return jsonify({"agents": agents})


@app.route("/api/workflows", methods=["GET"])
def get_workflows():
    """Return list of available workflows."""
    workflows = [
        {"name": "default", "description": "Full team collaboration"},
        {"name": "quick", "description": "Fast single-pass"},
        {"name": "thorough", "description": "Multi-review cycles"},
        {"name": "review-only", "description": "Code review only"},
        {"name": "document", "description": "Documentation focus"},
    ]
    return jsonify({"workflows": workflows})


@app.route("/api/models/status", methods=["GET"])
def get_models_status():
    """Return local model backend and model status from team config."""
    if not engine:
        _init_engine()

    agents_config = engine.config.get("agents", {})
    if not isinstance(agents_config, dict):
        agents_config = {}
    backend_probe_cache: Dict[str, Dict[str, Any]] = {}
    backend_status_map: Dict[str, Dict[str, Any]] = {}
    local_agents = []

    for agent_name, agent_config in agents_config.items():
        backend_type = _canonical_local_backend_type(agent_config.get("type"))
        if backend_type is None:
            continue

        endpoint = str(
            agent_config.get("endpoint") or LOCAL_BACKEND_DEFAULT_ENDPOINTS.get(backend_type, "")
        ).rstrip("/")
        if not endpoint:
            endpoint = LOCAL_BACKEND_DEFAULT_ENDPOINTS.get(backend_type, "")

        probe_key = f"{backend_type}::{endpoint}"
        if probe_key not in backend_probe_cache:
            backend_probe_cache[probe_key] = _probe_local_backend(backend_type, endpoint)
        probe = backend_probe_cache[probe_key]

        configured_model = agent_config.get("model")
        configured_model_present = None
        if isinstance(configured_model, str) and configured_model.strip():
            configured_model_present = configured_model in set(probe.get("models", []))

        enabled = bool(agent_config.get("enabled", False))
        agent_status = {
            "name": agent_name,
            "type": str(agent_config.get("type", "")),
            "backend_type": backend_type,
            "enabled": enabled,
            "offline": bool(agent_config.get("offline", False)),
            "endpoint": endpoint,
            "capabilities": agent_config.get("capabilities", []),
            "configured_model": configured_model,
            "configured_model_present": configured_model_present,
            "endpoint_online": bool(probe.get("online", False)),
            "available_for_execution": enabled and bool(probe.get("online", False)),
            "model_count": len(probe.get("models", [])),
            "discovered_models": probe.get("models", []),
            "probe_error": probe.get("error"),
        }
        local_agents.append(agent_status)

        backend = backend_status_map.get(probe_key)
        if backend is None:
            backend = {
                "backend_type": backend_type,
                "endpoint": endpoint,
                "online": bool(probe.get("online", False)),
                "models": list(probe.get("models", [])),
                "models_detailed": list(probe.get("models_detailed", [])),
                "model_count": len(probe.get("models", [])),
                "agents": [],
                "enabled_agents": 0,
                "available_agents": 0,
                "probe_error": probe.get("error"),
            }
            backend_status_map[probe_key] = backend

        backend["agents"].append(agent_name)
        if enabled:
            backend["enabled_agents"] += 1
        if agent_status["available_for_execution"]:
            backend["available_agents"] += 1

    backends = sorted(
        backend_status_map.values(),
        key=lambda item: (item.get("backend_type", ""), item.get("endpoint", "")),
    )
    local_agents = sorted(local_agents, key=lambda item: item.get("name", ""))

    summary = {
        "local_agents": len(local_agents),
        "enabled_local_agents": sum(1 for item in local_agents if item.get("enabled")),
        "online_backends": sum(1 for item in backends if item.get("online")),
        "backends": len(backends),
        "models": sum(int(item.get("model_count", 0)) for item in backends),
    }

    return jsonify({"summary": summary, "backends": backends, "agents": local_agents})


@socketio.on("connect")
def on_connect():
    """Join socket client to its room and emit initial session status."""
    client_id = _normalize_client_id(request.args.get("client_id"))
    join_room(client_id)
    with session_lock:
        sid_to_client[request.sid] = client_id
    snapshot = _get_session_snapshot(client_id)
    emit(
        "connected",
        {
            "message": "Connected to Agentic Team UI",
            "status": snapshot.get("status", "idle"),
            "client_id": client_id,
        },
    )


@socketio.on("disconnect")
def on_disconnect():
    """Clean up room mapping for disconnected socket clients."""
    with session_lock:
        sid_to_client.pop(request.sid, None)


if __name__ == "__main__":
    _init_engine()
    port = int(os.environ.get("AGENTIC_UI_BACKEND_PORT") or os.environ.get("PORT", "5002"))
    host = os.environ.get("AGENTIC_UI_BACKEND_HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
