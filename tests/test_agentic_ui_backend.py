"""Tests for standalone agentic UI backend."""

from types import SimpleNamespace
from unittest.mock import Mock

import agentic_team.ui.app as agentic_app


def _reset_state():
    with agentic_app.session_lock:
        agentic_app.client_sessions.clear()
        agentic_app.sid_to_client.clear()


def test_health_endpoint():
    _reset_state()
    with agentic_app.app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "healthy"


def test_get_team_config_uses_engine():
    _reset_state()
    original_engine = agentic_app.engine
    try:
        team_config = {"lead_role": "project_manager", "roles": {}}
        agentic_app.engine = SimpleNamespace(
            get_team_config=Mock(return_value=team_config),
            get_available_agents=Mock(return_value=["claude"]),
        )
        with agentic_app.app.test_client() as client:
            response = client.get("/api/team/config")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["team"]["lead_role"] == "project_manager"
        assert payload["agents"] == ["claude"]
    finally:
        agentic_app.engine = original_engine


def test_emit_team_turn_broadcasts_communication_and_log():
    _reset_state()
    original_emit = agentic_app.socketio.emit
    try:
        agentic_app.socketio.emit = Mock()
        agentic_app._emit_team_turn(
            "c-turn",
            {
                "turn": 2,
                "action": "message",
                "from_role": "software_developer",
                "to_role": "qa_engineer",
                "from_agent": "codex",
                "to_agent": "gemini",
                "message": "Please validate implementation.",
                "success": True,
            },
        )

        event_names = [call.args[0] for call in agentic_app.socketio.emit.call_args_list]
        assert "team_turn" in event_names
        assert "team_communication" in event_names
        assert "progress_log" in event_names

        snapshot = agentic_app._get_session_snapshot("c-turn")
        assert len(snapshot["team_turns"]) == 1
        assert snapshot["team_turns"][0]["from_role"] == "software_developer"
    finally:
        agentic_app.socketio.emit = original_emit


def test_execute_starts_background_task():
    _reset_state()
    original_engine = agentic_app.engine
    original_start_background_task = agentic_app.socketio.start_background_task
    try:
        agentic_app.engine = SimpleNamespace(
            get_team_config=Mock(
                return_value={
                    "lead_role": "project_manager",
                    "roles": {"project_manager": {"agent": "claude"}},
                }
            ),
            get_available_agents=Mock(return_value=["claude"]),
        )
        agentic_app.socketio.start_background_task = Mock()
        with agentic_app.app.test_client() as client:
            response = client.post(
                "/api/execute",
                json={"task": "build endpoint", "max_turns": 7, "client_id": "c1"},
            )
        assert response.status_code == 200
        assert agentic_app.socketio.start_background_task.call_count == 1
    finally:
        agentic_app.engine = original_engine
        agentic_app.socketio.start_background_task = original_start_background_task


def test_put_config_updates_file_and_reloads(tmp_path, monkeypatch):
    _reset_state()
    config_file = tmp_path / "agents.yaml"
    config_file.write_text("agents: {}\nworkflows: {}\nsettings: {}\n", encoding="utf-8")
    monkeypatch.setenv("AGENTIC_TEAM_CONFIG_PATH", str(config_file))

    init_calls = {"count": 0}
    original_init = agentic_app._init_engine
    original_validation = agentic_app._team_validation_payload

    def fake_init():
        init_calls["count"] += 1

    try:
        agentic_app._init_engine = fake_init
        agentic_app._team_validation_payload = lambda: {
            "valid": True,
            "available_agents": ["codex"],
            "missing_roles": [],
        }
        with agentic_app.app.test_client() as client:
            response = client.put(
                "/api/config",
                json={
                    "content": (
                        "agents:\n  codex:\n    enabled: true\n"
                        "workflows:\n  default: []\n"
                        "settings:\n  max_iterations: 2\n"
                        "agentic_team:\n  lead_role: project_manager\n"
                    )
                },
            )
        assert response.status_code == 200
        payload = response.get_json()
        assert "reloaded" not in payload or payload["message"]
        assert init_calls["count"] == 1
        assert "agentic_team" in config_file.read_text(encoding="utf-8")
    finally:
        agentic_app._init_engine = original_init
        agentic_app._team_validation_payload = original_validation


def test_get_config_returns_parsed_payload(tmp_path, monkeypatch):
    _reset_state()
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(
        "agents:\n  codex:\n    enabled: true\nworkflows: {}\nsettings: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_TEAM_CONFIG_PATH", str(config_file))

    with agentic_app.app.test_client() as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.get_json()
    assert "parsed" in payload
    assert payload["parsed"]["agents"]["codex"]["enabled"] is True


def test_put_config_accepts_structured_object(tmp_path, monkeypatch):
    _reset_state()
    config_file = tmp_path / "agents.yaml"
    config_file.write_text("agents: {}\nworkflows: {}\nsettings: {}\n", encoding="utf-8")
    monkeypatch.setenv("AGENTIC_TEAM_CONFIG_PATH", str(config_file))

    original_init = agentic_app._init_engine
    original_validation = agentic_app._team_validation_payload
    init_calls = {"count": 0}

    def fake_init():
        init_calls["count"] += 1

    try:
        agentic_app._init_engine = fake_init
        agentic_app._team_validation_payload = lambda: {
            "valid": True,
            "available_agents": ["codex"],
            "missing_roles": [],
        }
        with agentic_app.app.test_client() as client:
            response = client.put(
                "/api/config",
                json={
                    "config": {
                        "agents": {"codex": {"enabled": True, "type": "cli"}},
                        "workflows": {"default": {"steps": []}},
                        "settings": {"max_iterations": 3},
                        "agentic_team": {"lead_role": "project_manager", "roles": {}},
                    }
                },
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["parsed"]["settings"]["max_iterations"] == 3
        assert init_calls["count"] == 1
    finally:
        agentic_app._init_engine = original_init
        agentic_app._team_validation_payload = original_validation


def test_execute_rejects_invalid_team_mapping():
    _reset_state()
    original_engine = agentic_app.engine
    try:
        agentic_app.engine = SimpleNamespace(
            get_team_config=Mock(
                return_value={
                    "lead_role": "project_manager",
                    "roles": {
                        "project_manager": {"agent": "claude"},
                        "qa_engineer": {"agent": "copilot"},
                    },
                }
            ),
            get_available_agents=Mock(return_value=["claude"]),
        )
        with agentic_app.app.test_client() as client:
            response = client.post(
                "/api/execute",
                json={"task": "run tests", "max_turns": 6, "client_id": "c2"},
            )
        assert response.status_code == 400
        payload = response.get_json()
        assert "unavailable agents" in payload["error"].lower()
        assert payload["validation"]["valid"] is False
    finally:
        agentic_app.engine = original_engine


def test_execute_rejects_when_no_available_agents():
    _reset_state()
    original_engine = agentic_app.engine
    try:
        agentic_app.engine = SimpleNamespace(
            get_team_config=Mock(
                return_value={
                    "lead_role": "project_manager",
                    "roles": {
                        "project_manager": {"agent": "claude"},
                    },
                }
            ),
            get_available_agents=Mock(return_value=[]),
        )
        with agentic_app.app.test_client() as client:
            response = client.post(
                "/api/execute",
                json={"task": "run tests", "max_turns": 6, "client_id": "c3"},
            )
        assert response.status_code == 400
        payload = response.get_json()
        assert "no available agents" in payload["error"].lower()
        assert payload["validation"]["reason"] == "no_available_agents"
    finally:
        agentic_app.engine = original_engine
