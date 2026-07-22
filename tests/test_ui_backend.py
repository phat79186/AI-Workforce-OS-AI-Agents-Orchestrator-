"""Tests for UI backend session and workflow endpoints."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import orchestrator.ui.app as ui_app


def _reset_session_state():
    with ui_app.session_lock:
        ui_app.client_sessions.clear()
        ui_app.sid_to_client.clear()


def test_get_workflows_supports_structured_and_legacy_formats():
    _reset_session_state()
    original_orchestrator = ui_app.orchestrator

    try:
        ui_app.orchestrator = SimpleNamespace(
            config={
                "workflows": {
                    "default": {
                        "description": "Primary workflow",
                        "offline": False,
                        "steps": [
                            {"agent": "codex", "role": "implementer"},
                            {"agent": "claude", "task": "review", "fallback": "local-instruct"},
                        ],
                    },
                    "legacy": [
                        {"agent": "codex", "task": "implement"},
                        {"agent": "gemini", "task": "review"},
                    ],
                }
            }
        )

        with ui_app.app.test_client() as client:
            response = client.get("/api/workflows")

        assert response.status_code == 200
        payload = response.get_json()
        workflows = {item["name"]: item for item in payload["workflows"]}

        assert workflows["default"]["offline"] is False
        assert workflows["default"]["steps"][0]["task"] == "implement"
        assert workflows["default"]["steps"][1]["fallback"] == "local-instruct"
        assert workflows["legacy"]["steps"][1]["task"] == "review"
    finally:
        ui_app.orchestrator = original_orchestrator


def test_emit_progress_log_persists_to_status_session():
    _reset_session_state()
    original_emit = ui_app.socketio.emit

    try:
        ui_app.socketio.emit = Mock()
        ui_app._emit_progress_log("client-a", {"message": "progress update", "level": "info"})

        with ui_app.app.test_client() as client:
            response = client.get("/api/status?client_id=client-a")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["logs"][-1]["message"] == "progress update"
        assert payload["logs"][-1]["level"] == "info"
        assert payload["client_id"] == "client-a"
        ui_app.socketio.emit.assert_called_once()
    finally:
        ui_app.socketio.emit = original_emit


def test_clear_conversation_resets_logs():
    _reset_session_state()
    with ui_app.session_lock:
        ui_app.client_sessions["client-a"] = ui_app._new_session_state()
        ui_app.client_sessions["client-a"]["logs"] = [
            {"message": "old", "level": "info", "timestamp": "x"}
        ]
        ui_app.client_sessions["client-a"]["status"] = "running"

    with ui_app.app.test_client() as client:
        clear_response = client.post("/api/conversation/clear", json={"client_id": "client-a"})
        status_response = client.get("/api/status?client_id=client-a")

    assert clear_response.status_code == 200
    assert status_response.status_code == 200
    payload = status_response.get_json()
    assert payload["status"] == "idle"
    assert payload["logs"] == []


def test_sessions_are_isolated_per_client():
    _reset_session_state()
    with ui_app.session_lock:
        ui_app.client_sessions["client-a"] = ui_app._new_session_state()
        ui_app.client_sessions["client-a"]["status"] = "running"
        ui_app.client_sessions["client-a"]["task"] = "task a"
        ui_app.client_sessions["client-b"] = ui_app._new_session_state()
        ui_app.client_sessions["client-b"]["status"] = "idle"
        ui_app.client_sessions["client-b"]["task"] = "task b"

    with ui_app.app.test_client() as client:
        response_a = client.get("/api/status?client_id=client-a")
        response_b = client.get("/api/status?client_id=client-b")

    payload_a = response_a.get_json()
    payload_b = response_b.get_json()
    assert payload_a["status"] == "running"
    assert payload_a["task"] == "task a"
    assert payload_b["status"] == "idle"
    assert payload_b["task"] == "task b"


def test_execute_creates_independent_running_sessions_per_client():
    _reset_session_state()
    original_orchestrator = ui_app.orchestrator
    original_start_bg = ui_app.socketio.start_background_task

    try:
        ui_app.orchestrator = SimpleNamespace(config={"agents": {}, "workflows": {}})
        ui_app.socketio.start_background_task = Mock()

        with ui_app.app.test_client() as client:
            response_a = client.post(
                "/api/execute",
                json={"task": "task a", "workflow": "default", "client_id": "client-a"},
            )
            response_b = client.post(
                "/api/execute",
                json={"task": "task b", "workflow": "default", "client_id": "client-b"},
            )
            status_a = client.get("/api/status?client_id=client-a")
            status_b = client.get("/api/status?client_id=client-b")

        assert response_a.status_code == 200
        assert response_b.status_code == 200
        payload_a = status_a.get_json()
        payload_b = status_b.get_json()
        assert payload_a["status"] == "running"
        assert payload_a["task"] == "task a"
        assert payload_b["status"] == "running"
        assert payload_b["task"] == "task b"
        assert ui_app.socketio.start_background_task.call_count == 2
    finally:
        ui_app.orchestrator = original_orchestrator
        ui_app.socketio.start_background_task = original_start_bg


def test_models_status_returns_detailed_local_backend_data():
    _reset_session_state()
    original_orchestrator = ui_app.orchestrator

    class _FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self):
            return self._payload

    def fake_get(url, timeout=0):
        if url.endswith("/api/tags"):
            return _FakeResponse(
                200,
                {
                    "models": [
                        {"name": "codellama:13b", "size": 8800000000, "modified_at": "now"},
                        {"name": "mistral:7b", "size": 4100000000, "modified_at": "now"},
                    ]
                },
            )
        if url.endswith("/v1/models"):
            return _FakeResponse(
                200,
                {"data": [{"id": "qwen2.5-coder", "owned_by": "local"}]},
            )
        if url.endswith("/health") or url.endswith("http://localhost:8080"):
            return _FakeResponse(200, {})
        raise RuntimeError(f"unexpected url: {url}")

    try:
        ui_app.orchestrator = SimpleNamespace(
            config={
                "agents": {
                    "local-code": {
                        "type": "ollama",
                        "enabled": True,
                        "offline": True,
                        "endpoint": "http://localhost:11434",
                        "model": "codellama:13b",
                    },
                    "local-large": {
                        "type": "llamacpp",
                        "enabled": False,
                        "offline": True,
                        "endpoint": "http://localhost:8080",
                        "model": "qwen2.5-coder",
                    },
                }
            },
            adapters={},
        )

        with patch("orchestrator.ui.app.httpx.get", side_effect=fake_get):
            with ui_app.app.test_client() as client:
                response = client.get("/api/models/status")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["summary"]["local_agents"] == 2
        assert payload["summary"]["backends"] == 2
        agents = {item["name"]: item for item in payload["agents"]}
        assert agents["local-code"]["configured_model_present"] is True
        assert agents["local-code"]["available_for_execution"] is True
        assert agents["local-large"]["enabled"] is False
        assert agents["local-large"]["available_for_execution"] is False
        backends = {item["endpoint"]: item for item in payload["backends"]}
        assert backends["http://localhost:11434"]["model_count"] == 2
        assert backends["http://localhost:8080"]["online"] is True
    finally:
        ui_app.orchestrator = original_orchestrator


def test_config_endpoints_support_structured_payload(monkeypatch, tmp_path):
    _reset_session_state()
    original_init = ui_app.init_orchestrator
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(
        "agents: {}\nworkflows: {}\nsettings:\n  max_iterations: 3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_ORCHESTRATOR_CONFIG_PATH", str(config_file))

    init_calls = {"count": 0}

    def fake_init():
        init_calls["count"] += 1

    try:
        ui_app.init_orchestrator = fake_init
        with ui_app.app.test_client() as client:
            get_response = client.get("/api/config")
            put_response = client.put(
                "/api/config",
                json={
                    "config": {
                        "agents": {"codex": {"enabled": True, "type": "cli"}},
                        "workflows": {"default": {"steps": []}},
                        "settings": {"max_iterations": 2},
                        "agentic_team": {"lead_role": "project_manager", "roles": {}},
                    }
                },
            )

        assert get_response.status_code == 200
        get_payload = get_response.get_json()
        assert isinstance(get_payload["parsed"], dict)
        assert "settings" in get_payload["parsed"]

        assert put_response.status_code == 200
        put_payload = put_response.get_json()
        assert "updated" in put_payload["message"].lower()
        assert put_payload["parsed"]["settings"]["max_iterations"] == 2
        assert init_calls["count"] == 1
        assert "agentic_team" in config_file.read_text(encoding="utf-8")
    finally:
        ui_app.init_orchestrator = original_init
