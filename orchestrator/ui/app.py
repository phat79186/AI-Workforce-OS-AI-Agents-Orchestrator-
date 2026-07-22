# pylint: disable=too-many-lines
"""
Web UI Backend for AI Orchestrator

Provides a REST API and WebSocket interface for the web-based UI with conversation support.
"""

import json
import logging
import os
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock, get_ident
from typing import Any, Dict, List, Optional

import httpx
import yaml
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that emits logs via WebSocket."""

    def __init__(self, socketio_instance, progress_callback=None):
        super().__init__()
        self.socketio = socketio_instance
        self.progress_callback = progress_callback
        self.owner_thread_id = get_ident()
        # Set a simple formatter
        formatter = logging.Formatter("%(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit log record via WebSocket."""
        try:
            # Prevent cross-job log leakage when multiple tasks run concurrently.
            if record.thread != self.owner_thread_id:
                return

            if not any(
                record.name.startswith(prefix)
                for prefix in ["orchestrator", "workflow", "adapter", "task_manager"]
            ):
                return

            log_entry = self.format(record)
            level = record.levelname.lower()
            timestamp = datetime.now().isoformat()

            try:
                # Attempt to parse structured JSON log
                log_data = json.loads(log_entry)
                payload = {**log_data, "level": level, "timestamp": timestamp}
            except json.JSONDecodeError:
                # Fallback for plain string logs
                payload = {"message": log_entry, "level": level, "timestamp": timestamp}

            if self.progress_callback:
                self.progress_callback(payload)
            else:
                self.socketio.emit("progress_log", payload, namespace="/")
        except Exception as e:
            logging.getLogger(__name__).debug("WebSocketLogHandler error: %s", e)


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.core.engine import (  # noqa: E402  # pylint: disable=wrong-import-position
    Orchestrator,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())
CORS(app, origins=os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(","))
socketio = SocketIO(
    app,
    cors_allowed_origins=os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(","),
    async_mode="threading",
    allow_upgrades=False,  # threading mode only supports polling, prevent WebSocket 500
)
FRONTEND_PUBLIC_DIR = Path(__file__).parent / "frontend" / "public"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[Any] = None
session_lock = Lock()
MAX_SESSION_LOGS = 500
DEFAULT_CLIENT_ID = "default"
client_sessions: Dict[str, Dict[str, Any]] = {}
sid_to_client: Dict[str, str] = {}
LOCAL_BACKEND_DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai-compatible": "http://localhost:8080",
}


def _new_session_state() -> Dict[str, Any]:
    """Create a fresh session state object."""
    return {
        "task": None,
        "workflow": "default",
        "status": "idle",
        "cancelled": False,
        "results": None,
        "files": [],
        "conversation_history": [],
        "last_task": None,
        "last_output": None,
        "context": {},
        "logs": [],
        "started_at": None,
        "updated_at": datetime.now().isoformat(),
    }


def _normalize_client_id(raw_client_id: Optional[str]) -> str:
    """Normalize external client id into an internal safe key."""
    if not isinstance(raw_client_id, str):
        return DEFAULT_CLIENT_ID
    client_id = raw_client_id.strip()
    if not client_id:
        return DEFAULT_CLIENT_ID
    return client_id[:128]


def _get_client_id_from_request(payload: Optional[Dict[str, Any]] = None) -> str:
    """Resolve client id from payload/query/header with sane fallback."""
    payload_client_id = None
    if isinstance(payload, dict):
        payload_client_id = payload.get("client_id")
    header_client_id = request.headers.get("X-Client-Id")
    query_client_id = request.args.get("client_id")
    return _normalize_client_id(payload_client_id or query_client_id or header_client_id)


def _get_or_create_session(client_id: str) -> Dict[str, Any]:
    """Get session for client, creating one if missing."""
    normalized_client_id = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.get(normalized_client_id)
        if session is None:
            session = _new_session_state()
            client_sessions[normalized_client_id] = session
        return session


def _get_session_snapshot(client_id: str) -> Dict[str, Any]:
    """Get deep copy of a client session for response serialization."""
    normalized_client_id = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.get(normalized_client_id)
        if session is None:
            session = _new_session_state()
            client_sessions[normalized_client_id] = session
        return deepcopy(session)


def _record_progress_log(client_id: str, payload: Dict[str, Any]) -> None:
    """Persist progress logs in session state for polling-based UI updates."""
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return

    entry = {
        "message": message.strip(),
        "level": str(payload.get("level", "info")).lower(),
        "timestamp": payload.get("timestamp") or datetime.now().isoformat(),
    }

    normalized_client_id = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.setdefault(normalized_client_id, _new_session_state())
        logs = session.setdefault("logs", [])
        logs.append(entry)
        if len(logs) > MAX_SESSION_LOGS:
            del logs[: len(logs) - MAX_SESSION_LOGS]
        session["updated_at"] = datetime.now().isoformat()


def _emit_progress_log(client_id: str, payload: Dict[str, Any]) -> None:
    """Emit progress log over socket and persist it in session state."""
    if "timestamp" not in payload:
        payload = {**payload, "timestamp": datetime.now().isoformat()}
    _record_progress_log(client_id, payload)
    socketio.emit("progress_log", payload, namespace="/", to=_normalize_client_id(client_id))


def init_orchestrator() -> None:
    """Initialize the orchestrator."""
    global orchestrator
    config_path = _config_path()
    orchestrator = Orchestrator(str(config_path))


def _config_path() -> Path:
    """Resolve config path from env override or default project path."""
    override = os.getenv("AI_ORCHESTRATOR_CONFIG_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).parent.parent / "config" / "agents.yaml"


def _validate_config_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate config payload from JSON body and return normalized config dict."""
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
    """Serialize config object to YAML string."""
    return yaml.safe_dump(
        config_obj,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=False,
    )


def _normalize_workflow_steps(workflow_config: Any) -> List[Dict[str, Any]]:
    """Normalize workflow config to a list of step dictionaries."""
    if isinstance(workflow_config, list):
        return [step for step in workflow_config if isinstance(step, dict)]

    if isinstance(workflow_config, dict):
        steps = workflow_config.get("steps", [])
        if isinstance(steps, list):
            return [step for step in steps if isinstance(step, dict)]

    return []


def _normalize_step_task(step: Dict[str, Any]) -> str:
    """Normalize task field; fallback to role aliases used by new workflow format."""
    task = step.get("task")
    if isinstance(task, str) and task.strip():
        return task

    role = step.get("role")
    if not isinstance(role, str):
        return ""

    role_map = {
        "implementer": "implement",
        "reviewer": "review",
        "refiner": "refine",
        "writer": "document",
        "tester": "test",
    }
    return role_map.get(role.strip().lower(), role)


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
        models: List[str] = []
        models_detailed: List[Dict[str, Any]] = []
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
    except Exception as exc:
        return {"online": False, "models": [], "models_detailed": [], "error": str(exc)}


def _probe_openai_compatible_backend(endpoint: str) -> Dict[str, Any]:
    """Probe OpenAI-compatible local endpoint (llama.cpp/LocalAI/text-generation-webui)."""
    online = False
    health_error: Optional[str] = None

    for url in [f"{endpoint}/health", f"{endpoint}/v1/models", endpoint]:
        try:
            resp = httpx.get(url, timeout=2)
            if resp.status_code < 500:
                online = True
                break
        except Exception as exc:
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
        models: List[str] = []
        models_detailed: List[Dict[str, Any]] = []
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
    except Exception as exc:
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


def _serve_frontend_public_asset(filename: str, mimetype: Optional[str] = None):
    """Serve shared favicon/PWA assets from the frontend public directory."""
    return send_from_directory(str(FRONTEND_PUBLIC_DIR), filename, mimetype=mimetype)


@app.route("/favicon.ico")
def favicon():
    """Serve favicon.ico."""
    return _serve_frontend_public_asset("favicon.ico", "image/x-icon")


@app.route("/favicon-16x16.png")
def favicon_16():
    """Serve 16x16 favicon."""
    return _serve_frontend_public_asset("favicon-16x16.png", "image/png")


@app.route("/favicon-32x32.png")
def favicon_32():
    """Serve 32x32 favicon."""
    return _serve_frontend_public_asset("favicon-32x32.png", "image/png")


@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    """Serve Apple touch icon."""
    return _serve_frontend_public_asset("apple-touch-icon.png", "image/png")


@app.route("/android-chrome-192x192.png")
def android_chrome_192():
    """Serve Android chrome 192x192 icon."""
    return _serve_frontend_public_asset("android-chrome-192x192.png", "image/png")


@app.route("/android-chrome-512x512.png")
def android_chrome_512():
    """Serve Android chrome 512x512 icon."""
    return _serve_frontend_public_asset("android-chrome-512x512.png", "image/png")


@app.route("/site.webmanifest")
def site_webmanifest():
    """Serve site web manifest."""
    return _serve_frontend_public_asset("site.webmanifest", "application/manifest+json")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return raw and parsed orchestrator configuration."""
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
        # Keep endpoint resilient even if file is temporarily malformed.
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
    """Update orchestrator config from structured JSON object or YAML content."""
    data = request.get_json(silent=True) or {}
    try:
        parsed = _validate_config_payload(data)
        serialized = _dump_config_yaml(parsed)

        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
        init_orchestrator()

        return jsonify(
            {
                "message": "Configuration updated and orchestrator reloaded",
                "path": str(path),
                "content": serialized,
                "parsed": parsed,
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.error("Config update failed: %s", exc, exc_info=True)
        return jsonify({"error": f"Failed to update config: {exc}"}), 500


@app.route("/")
def index():
    """Serve the Vue frontend build."""
    dist_index = Path(__file__).parent / "frontend" / "dist" / "index.html"
    if dist_index.exists():
        return dist_index.read_text(encoding="utf-8")
    # Fallback to legacy template if dist not built
    return render_template("index.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serve Vue frontend built assets (JS, CSS)."""
    dist_dir = Path(__file__).parent / "frontend" / "dist" / "assets"
    return send_from_directory(str(dist_dir), filename)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Kubernetes liveness probe."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200


@app.route("/ready", methods=["GET"])
def readiness():
    """Readiness check endpoint for Kubernetes readiness probe."""
    try:
        # Check if orchestrator is initialized
        if orchestrator is None:
            return (
                jsonify(
                    {
                        "status": "not ready",
                        "reason": "orchestrator not initialized",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                503,
            )

        # Check if agents are available
        agents_available = any(adapter.is_available() for adapter in orchestrator.adapters.values())

        if not agents_available:
            return (
                jsonify(
                    {
                        "status": "not ready",
                        "reason": "no agents available",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                503,
            )

        return (
            jsonify(
                {
                    "status": "ready",
                    "agents_count": len(orchestrator.adapters),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify(
                {"status": "not ready", "reason": str(e), "timestamp": datetime.now().isoformat()}
            ),
            503,
        )


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus-compatible metrics endpoint."""
    try:
        if not orchestrator:
            init_orchestrator()

        # Gather metrics
        agents_total = len(orchestrator.adapters)
        agents_available = sum(
            1 for adapter in orchestrator.adapters.values() if adapter.is_available()
        )
        with session_lock:
            active_sessions = sum(
                1 for session in client_sessions.values() if session.get("status") == "running"
            )
            total_sessions = len(client_sessions)

        metrics_output = f"""# HELP ai_orchestrator_agents_total Total number of agents
# TYPE ai_orchestrator_agents_total gauge
ai_orchestrator_agents_total {agents_total}

# HELP ai_orchestrator_agents_available Number of available agents
# TYPE ai_orchestrator_agents_available gauge
ai_orchestrator_agents_available {agents_available}

# HELP ai_orchestrator_session_active Is there an active session
# TYPE ai_orchestrator_session_active gauge
ai_orchestrator_session_active {active_sessions}

# HELP ai_orchestrator_sessions_total Total number of known client sessions
# TYPE ai_orchestrator_sessions_total gauge
ai_orchestrator_sessions_total {total_sessions}

# HELP ai_orchestrator_up Service is up
# TYPE ai_orchestrator_up gauge
ai_orchestrator_up 1
"""
        return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
    except Exception as e:
        logger.error("Error generating metrics: %s", e)
        return (
            f"# Error generating metrics: {str(e)}\n",
            500,
            {"Content-Type": "text/plain; version=0.0.4"},
        )


@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Get list of available agents."""
    if not orchestrator:
        init_orchestrator()

    agents_config = orchestrator.config.get("agents", {})
    agents_list = []

    for name, adapter in orchestrator.adapters.items():
        agent_config = agents_config.get(name, {})
        agents_list.append(
            {
                "name": name,
                "enabled": agent_config.get("enabled", False),
                "role": agent_config.get("role", ""),
                "description": agent_config.get("description", ""),
                "available": adapter.is_available(),
            }
        )

    return jsonify({"agents": agents_list})


@app.route("/api/models/status", methods=["GET"])
def get_local_models_status():
    """Get detailed status for configured local model backends and agents."""
    if not orchestrator:
        init_orchestrator()

    agents_config = orchestrator.config.get("agents", {})
    backend_probe_cache: Dict[str, Dict[str, Any]] = {}
    backend_status_map: Dict[str, Dict[str, Any]] = {}
    local_agents: List[Dict[str, Any]] = []

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
        configured_model_present: Optional[bool] = None
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


@app.route("/api/workflows", methods=["GET"])
def get_workflows():
    """Get list of available workflows."""
    if not orchestrator:
        init_orchestrator()

    workflows_config = orchestrator.config.get("workflows", {})
    workflows_list = []

    for name, workflow_config in workflows_config.items():
        steps = _normalize_workflow_steps(workflow_config)
        description = ""
        offline = False

        if isinstance(workflow_config, dict):
            description = workflow_config.get("description", "")
            offline = bool(workflow_config.get("offline", False))
        elif steps:
            description = steps[0].get("description", "")

        workflow_info = {
            "name": name,
            "description": description,
            "offline": offline,
            "steps": [
                {
                    "agent": step.get("agent"),
                    "task": _normalize_step_task(step),
                    "description": step.get("description", ""),
                    "fallback": step.get("fallback"),
                }
                for step in steps
            ],
        }
        workflows_list.append(workflow_info)

    return jsonify({"workflows": workflows_list})


@app.route("/api/execute", methods=["POST"])
def execute_task():
    """Execute a task via the API with conversation support."""
    data = request.get_json(silent=True) or {}
    task = data.get("task")
    workflow = data.get("workflow", "default")
    max_iterations = data.get("max_iterations", 3)
    is_followup = data.get("is_followup", False)
    client_id = _get_client_id_from_request(data)

    if not task or not isinstance(task, str) or not task.strip():
        return jsonify({"error": "Task is required and must be a non-empty string"}), 400
    task = task.strip()
    if len(task) > 50000:
        return jsonify({"error": "Task exceeds maximum length of 50000 characters"}), 400

    try:
        max_iterations = max(1, min(10, int(max_iterations)))
    except (TypeError, ValueError):
        max_iterations = 3

    if not orchestrator:
        init_orchestrator()

    # Handle follow-up context
    actual_task = task
    session = _get_or_create_session(client_id)
    if is_followup and session.get("last_task"):
        # Inject previous context for follow-ups in this client session.
        previous_task = session["last_task"]
        previous_output = session.get("last_output", "")
        actual_task = f"Previous task: {previous_task}\nPrevious result: {previous_output}\n\nFollow-up: {task}"

    # Update session
    with session_lock:
        session = client_sessions.setdefault(client_id, _new_session_state())
        session["task"] = task
        session["workflow"] = workflow
        session["status"] = "running"
        session["results"] = None
        session["files"] = []
        session["logs"] = []
        session["started_at"] = datetime.now().isoformat()
        session["updated_at"] = datetime.now().isoformat()

        # Add to conversation history
        session["conversation_history"].append(
            {
                "role": "user",
                "content": task,
                "is_followup": is_followup,
                "timestamp": datetime.now().isoformat(),
            }
        )

    # Execute via socket for real-time updates
    socketio.start_background_task(
        execute_task_async, client_id, actual_task, workflow, max_iterations, is_followup
    )

    return jsonify(
        {
            "message": "Task started",
            "session_id": datetime.now().isoformat(),
            "is_followup": is_followup,
            "client_id": client_id,
        }
    )


def execute_task_async(
    client_id: str, task: str, workflow: str, max_iterations: int, is_followup: bool = False
):
    """Execute task asynchronously and send updates via WebSocket."""
    normalized_client_id = _normalize_client_id(client_id)

    try:
        # Send start event to the originating client session only.
        socketio.emit(
            "task_started",
            {"task": task, "workflow": workflow, "is_followup": is_followup},
            namespace="/",
            to=normalized_client_id,
        )

        # Emit progress log
        _emit_progress_log(
            normalized_client_id,
            {"message": f"Starting task execution with workflow: {workflow}", "level": "info"},
        )

        # Setup logging handler to capture all orchestrator-related logs
        log_handler = WebSocketLogHandler(
            socketio,
            progress_callback=lambda payload: _emit_progress_log(normalized_client_id, payload),
        )
        log_handler.setLevel(logging.INFO)

        # Attach to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        # Keep track for cleanup
        loggers_to_capture = [root_logger]

        try:
            # Execute task
            results = orchestrator.execute_task(
                task=task, workflow_name=workflow, max_iterations=max_iterations
            )
        finally:
            # Remove handler after execution from all loggers
            for logger_obj in loggers_to_capture:
                logger_obj.removeHandler(log_handler)

        # Emit completion log
        _emit_progress_log(
            normalized_client_id, {"message": "Task execution completed", "level": "success"}
        )

        # Collect files from all iterations
        files_created = []
        for iteration in results.get("iterations", []):
            for step in iteration.get("steps", []):
                if step.get("files_modified"):
                    files_created.extend(step["files_modified"])

        final_output = results.get("final_output", "")

        # Also extract file paths from agent output (markdown links, paths)
        if final_output:
            import re

            # Match markdown links: [name](path)
            for match in re.finditer(r"\[.*?\]\((/[^\)]+\.\w+)\)", final_output):
                p = match.group(1)
                if p not in files_created and Path(p).exists():
                    files_created.append(p)
            # Match bare absolute paths to known extensions
            for match in re.finditer(
                r"(/\S+\.(?:py|js|ts|java|go|rs|yaml|json|md|html|css|sh|sql|txt))\b",
                final_output,
            ):
                p = match.group(1)
                if p not in files_created and Path(p).exists():
                    files_created.append(p)
        with session_lock:
            session = client_sessions.setdefault(normalized_client_id, _new_session_state())
            session["results"] = results
            session["files"] = files_created
            session["status"] = "completed" if results.get("success") else "failed"

            # Store for future follow-ups
            session["last_task"] = session["task"]
            session["last_output"] = final_output
            session["context"]["files"] = files_created
            session["context"]["workspace"] = "./workspace"
            session["updated_at"] = datetime.now().isoformat()

            # Add to conversation history
            session["conversation_history"].append(
                {
                    "role": "assistant",
                    "content": final_output,
                    "files": files_created,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Send completion event
        socketio.emit(
            "task_completed",
            {
                "task": session.get("task"),
                "success": results.get("success"),
                "output": final_output,
                "files": files_created,
                "iterations": results.get("iterations", []),
                "can_followup": True,
            },
            namespace="/",
            to=normalized_client_id,
        )

    except Exception as e:
        logger.error("Error executing task: %s", e, exc_info=True)
        with session_lock:
            session = client_sessions.setdefault(normalized_client_id, _new_session_state())
            session["status"] = "error"
            session["updated_at"] = datetime.now().isoformat()
        _emit_progress_log(
            normalized_client_id, {"message": f"Task error: {str(e)}", "level": "error"}
        )
        socketio.emit("task_error", {"error": str(e)}, namespace="/", to=normalized_client_id)


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current session status."""
    client_id = _get_client_id_from_request()
    session_snapshot = _get_session_snapshot(client_id)
    session_snapshot["client_id"] = client_id
    return jsonify(session_snapshot)


@app.route("/api/conversation", methods=["GET"])
def get_conversation():
    """Get conversation history."""
    client_id = _get_client_id_from_request()
    session_snapshot = _get_session_snapshot(client_id)
    return jsonify(
        {
            "history": session_snapshot.get("conversation_history", []),
            "can_followup": bool(session_snapshot.get("last_task")),
            "client_id": client_id,
        }
    )


@app.route("/api/conversation/clear", methods=["POST"])
def clear_conversation():
    """Clear conversation history and start fresh."""
    data = request.get_json(silent=True) or {}
    client_id = _get_client_id_from_request(data)
    with session_lock:
        client_sessions[client_id] = _new_session_state()
    return jsonify({"message": "Conversation cleared", "client_id": client_id})


@app.route("/api/cancel", methods=["POST"])
def cancel_execution():
    """Cancel a running task execution."""
    data = request.get_json(silent=True) or {}
    client_id = _get_client_id_from_request(data)
    normalized = _normalize_client_id(client_id)
    with session_lock:
        session = client_sessions.get(normalized)
        if session and session.get("status") == "running":
            session["cancelled"] = True
            session["status"] = "cancelled"
            session["updated_at"] = datetime.now().isoformat()
    _emit_progress_log(normalized, {"message": "Execution cancelled by user", "level": "warn"})
    socketio.emit("task_cancelled", {"client_id": normalized}, namespace="/", to=normalized)
    return jsonify({"message": "Cancellation requested", "client_id": normalized})


@app.route("/api/files", methods=["GET"])
@app.route("/api/files/<path:filename>", methods=["GET"])
def get_file(filename=None):
    """Get file content. Accepts path as URL param or ?path= query param."""
    # Support both /api/files/<path> and /api/files?path=<path>
    if filename is None:
        filename = request.args.get("path", "")
    if not filename:
        return jsonify({"error": "No file path provided"}), 400

    project_root = Path(__file__).resolve().parent.parent.parent
    # Allowed directories: output/, workspace/, and the project root
    allowed_roots = [
        (project_root / "output").resolve(),
        (project_root / "workspace").resolve(),
        project_root.resolve(),
    ]

    # Handle absolute paths (from agent output) by checking they're under project root
    file_path = Path(filename)
    if file_path.is_absolute():
        file_path = file_path.resolve()
    else:
        # Try output/ first, then workspace/, then project root
        for root in allowed_roots:
            candidate = (root / filename).resolve()
            if candidate.exists():
                file_path = candidate
                break
        else:
            file_path = (allowed_roots[0] / filename).resolve()

    # Prevent path traversal — must be under project root
    if not str(file_path).startswith(str(project_root)):
        return jsonify({"error": "Access denied: path traversal detected"}), 403

    if not file_path.exists():
        return jsonify({"error": f"File not found: {filename}"}), 404

    # Skip binary files
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "Binary file — cannot display"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(
        {
            "filename": str(file_path.relative_to(project_root)),
            "content": content,
            "language": detect_language(filename),
        }
    )


def detect_language(filename: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "cpp",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sh": "shell",
        ".sql": "sql",
    }

    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "plaintext")


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
                # Skip unwanted files
                if any(skip in str(file_path) for skip in skip_patterns):
                    continue
                try:
                    rel_path = str(file_path.relative_to(project_root))
                    all_files.append(rel_path)
                except ValueError:
                    pass

    return jsonify({"files": sorted(all_files)})


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    client_id = _normalize_client_id(request.args.get("client_id"))
    join_room(client_id)
    with session_lock:
        sid_to_client[request.sid] = client_id
    logger.info("Client connected sid=%s client_id=%s", request.sid, client_id)
    session_snapshot = _get_session_snapshot(client_id)
    emit(
        "connected",
        {
            "message": "Connected to AI Orchestrator",
            "can_followup": bool(session_snapshot.get("last_task")),
            "status": session_snapshot.get("status", "idle"),
            "client_id": client_id,
        },
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    with session_lock:
        client_id = sid_to_client.pop(request.sid, None)
    logger.info("Client disconnected sid=%s client_id=%s", request.sid, client_id)


if __name__ == "__main__":
    init_orchestrator()
    port = int(os.environ.get("UI_BACKEND_PORT") or os.environ.get("PORT", "5001"))
    host = os.environ.get("UI_BACKEND_HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
