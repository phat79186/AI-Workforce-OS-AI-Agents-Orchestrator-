"""Tests for standalone agentic-team engine."""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml

from agentic_team import AgenticTeamEngine
from orchestrator.adapters import AgentResponse, BaseAdapter


def _write_config(tmp_path, payload: dict[str, Any]):
    config_file = tmp_path / "agentic_team_test_config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(payload, f)
    return config_file


def test_agentic_team_routes_between_roles_and_lead_finalizes(tmp_path, monkeypatch):
    class ScriptedAdapter(BaseAdapter):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if not hasattr(ScriptedAdapter, "_role_calls"):
                ScriptedAdapter._role_calls = {}

        def get_capabilities(self):
            return []

        def is_available(self) -> bool:
            return True

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            role = str(context.get("team_role", ""))
            ScriptedAdapter._role_calls[role] = ScriptedAdapter._role_calls.get(role, 0) + 1
            count = ScriptedAdapter._role_calls[role]

            if role == "project_manager" and count == 1:
                payload = {
                    "action": "message",
                    "to_role": "software_developer",
                    "message": "Implement the requested feature.",
                }
            elif role == "software_developer":
                payload = {
                    "action": "message",
                    "to_role": "qa_engineer",
                    "message": "Implementation done. Please validate.",
                }
            elif role == "qa_engineer":
                payload = {
                    "action": "message",
                    "to_role": "project_manager",
                    "message": "Validation passed. Ready for lead decision.",
                }
            else:
                payload = {
                    "action": "finalize",
                    "final_response": "Approved by team lead and ready for user.",
                }

            return AgentResponse(success=True, output=json.dumps(payload))

    def fake_resolver(self, agent_name, agent_config):
        if agent_config.get("type") == "scripted":
            return ScriptedAdapter
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)

    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "pm-agent": {"type": "scripted", "enabled": True},
                "dev-agent": {"type": "scripted", "enabled": True},
                "qa-agent": {"type": "scripted", "enabled": True},
                "arch-agent": {"type": "scripted", "enabled": True},
                "ops-agent": {"type": "scripted", "enabled": True},
            },
            "settings": {"max_iterations": 3},
            "agentic_team": {
                "lead_role": "project_manager",
                "max_turns": 8,
                "roles": {
                    "project_manager": {"agent": "pm-agent"},
                    "software_developer": {"agent": "dev-agent"},
                    "qa_engineer": {"agent": "qa-agent"},
                    "software_architect": {"agent": "arch-agent"},
                    "devops_engineer": {"agent": "ops-agent"},
                },
            },
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    result = engine.execute_task("Build API endpoint", max_turns=8)

    assert result["success"] is True
    assert "Approved by team lead" in result["final_output"]
    steps = result["iterations"][0]["steps"]
    assert [step["from_role"] for step in steps] == [
        "project_manager",
        "software_developer",
        "qa_engineer",
        "project_manager",
    ]
    assert steps[1]["to_role"] == "qa_engineer"
    assert steps[0]["from_agent"] == "pm-agent"
    assert steps[0]["to_agent"] == "dev-agent"
    assert steps[1]["from_agent"] == "dev-agent"
    assert steps[1]["to_agent"] == "qa-agent"
    assert steps[-1]["action"] == "finalize"


def test_agentic_team_allows_any_role_to_share_same_agent(tmp_path, monkeypatch):
    class SharedAdapter(BaseAdapter):
        def get_capabilities(self):
            return []

        def is_available(self) -> bool:
            return True

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            role = str(context.get("team_role", ""))
            if role == "project_manager":
                return AgentResponse(
                    success=True,
                    output=json.dumps(
                        {"action": "finalize", "final_response": "Shared-model team completed."}
                    ),
                )
            return AgentResponse(
                success=True,
                output=json.dumps(
                    {"action": "message", "to_role": "project_manager", "message": "Done"}
                ),
            )

    def fake_resolver(self, agent_name, agent_config):
        if agent_config.get("type") == "shared":
            return SharedAdapter
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)

    config_file = _write_config(
        tmp_path,
        {
            "agents": {"shared-agent": {"type": "shared", "enabled": True}},
            "agentic_team": {
                "lead_role": "project_manager",
                "max_turns": 4,
                "roles": {
                    "project_manager": {"agent": "shared-agent"},
                    "software_architect": {"agent": "shared-agent"},
                    "software_developer": {"agent": "shared-agent"},
                    "qa_engineer": {"agent": "shared-agent"},
                    "devops_engineer": {"agent": "shared-agent"},
                },
            },
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    result = engine.execute_task("Do work")

    assert result["success"] is True
    assert result["final_output"] == "Shared-model team completed."
    for role_spec in result["team"]["roles"].values():
        assert role_spec["agent"] == "shared-agent"


def test_agentic_team_raises_for_unavailable_role_mapping(tmp_path, monkeypatch):
    class OnlyAdapter(BaseAdapter):
        def get_capabilities(self):
            return []

        def is_available(self) -> bool:
            return True

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            return AgentResponse(success=True, output='{"action":"finalize","final_response":"ok"}')

    def fake_resolver(self, agent_name, agent_config):
        if agent_config.get("type") == "only":
            return OnlyAdapter
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)

    config_file = _write_config(
        tmp_path,
        {
            "agents": {"available-agent": {"type": "only", "enabled": True}},
            "agentic_team": {
                "lead_role": "project_manager",
                "roles": {
                    "project_manager": {"agent": "missing-agent"},
                    "software_architect": {"agent": "available-agent"},
                    "software_developer": {"agent": "available-agent"},
                    "qa_engineer": {"agent": "available-agent"},
                    "devops_engineer": {"agent": "available-agent"},
                },
            },
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    with pytest.raises(ValueError, match="unavailable agents"):
        engine.execute_task("Run")


def test_agentic_team_turn_callback_receives_each_turn(tmp_path, monkeypatch):
    class CallbackAdapter(BaseAdapter):
        def get_capabilities(self):
            return []

        def is_available(self) -> bool:
            return True

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            role = str(context.get("team_role", ""))
            if role == "project_manager":
                return AgentResponse(
                    success=True,
                    output=json.dumps(
                        {
                            "action": "finalize",
                            "final_response": "final",
                        }
                    ),
                )
            return AgentResponse(
                success=True,
                output=json.dumps(
                    {
                        "action": "message",
                        "to_role": "project_manager",
                        "message": "handoff",
                    }
                ),
            )

    def fake_resolver(self, agent_name, agent_config):
        if agent_config.get("type") == "callback":
            return CallbackAdapter
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)

    config_file = _write_config(
        tmp_path,
        {
            "agents": {"pm-agent": {"type": "callback", "enabled": True}},
            "agentic_team": {
                "lead_role": "project_manager",
                "max_turns": 3,
                "roles": {
                    "project_manager": {"agent": "pm-agent"},
                    "software_architect": {"agent": "pm-agent"},
                    "software_developer": {"agent": "pm-agent"},
                    "qa_engineer": {"agent": "pm-agent"},
                    "devops_engineer": {"agent": "pm-agent"},
                },
            },
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    callbacks = []
    engine.execute_task("Run task", turn_callback=lambda turn: callbacks.append(turn))
    assert len(callbacks) == 1
    assert callbacks[0]["turn"] == 1
    assert callbacks[0]["action"] == "finalize"


def test_team_defaults_pick_configured_agents_when_no_adapter_available(tmp_path, monkeypatch):
    def fake_resolver(self, agent_name, agent_config):
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)

    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "codex": {"type": "cli", "enabled": True},
                "gemini": {"type": "cli", "enabled": True},
                "claude": {"type": "cli", "enabled": True},
            },
            "agentic_team": {},
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    team = engine.get_team_config()
    for role_spec in team["roles"].values():
        assert isinstance(role_spec.get("agent"), str)
        assert role_spec["agent"]


def test_validate_team_bindings_reports_runtime_reason(tmp_path, monkeypatch):
    def fake_resolver(self, agent_name, agent_config):
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)
    config_file = _write_config(
        tmp_path,
        {
            "agents": {"codex": {"type": "cli", "enabled": True}},
            "agentic_team": {
                "lead_role": "project_manager",
                "roles": {
                    "project_manager": {"agent": "codex"},
                    "software_architect": {"agent": "codex"},
                    "software_developer": {"agent": "codex"},
                    "qa_engineer": {"agent": "codex"},
                    "devops_engineer": {"agent": "codex"},
                },
            },
        },
    )
    engine = AgenticTeamEngine(config_path=str(config_file))
    payload = engine.validate_team_bindings()
    assert payload["valid"] is False
    assert payload["reason"] == "no_available_agents"
    assert isinstance(payload["missing_roles"], list)


def test_execute_task_includes_production_metadata(tmp_path, monkeypatch):
    class FinalizeAdapter(BaseAdapter):
        def get_capabilities(self):
            return []

        def is_available(self) -> bool:
            return True

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            return AgentResponse(
                success=True,
                output=json.dumps({"action": "finalize", "final_response": "Ship it."}),
            )

    def fake_resolver(self, agent_name, agent_config):
        if agent_config.get("type") == "finalize":
            return FinalizeAdapter
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)
    config_file = _write_config(
        tmp_path,
        {
            "agents": {"pm-agent": {"type": "finalize", "enabled": True}},
            "agentic_team": {
                "lead_role": "project_manager",
                "roles": {
                    "project_manager": {"agent": "pm-agent"},
                    "software_architect": {"agent": "pm-agent"},
                    "software_developer": {"agent": "pm-agent"},
                    "qa_engineer": {"agent": "pm-agent"},
                    "devops_engineer": {"agent": "pm-agent"},
                },
            },
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    result = engine.execute_task("Deploy")

    assert result["success"] is True
    assert result["termination_reason"] == "lead_finalize"
    assert result["execution_id"]
    assert result["duration_ms"] >= 0
    assert result["stats"]["turns_executed"] == 1
    assert "started_at" in result
    assert "completed_at" in result
    assert result["iterations"][0]["steps"][0]["execution_id"] == result["execution_id"]
    assert result["iterations"][0]["steps"][0]["timestamp"]


def test_agentic_team_detects_repeated_route_and_escalates_to_lead(tmp_path, monkeypatch):
    class LoopSafeAdapter(BaseAdapter):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if not hasattr(LoopSafeAdapter, "_role_calls"):
                LoopSafeAdapter._role_calls = {}

        def get_capabilities(self):
            return []

        def is_available(self) -> bool:
            return True

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            role = str(context.get("team_role", ""))
            LoopSafeAdapter._role_calls[role] = LoopSafeAdapter._role_calls.get(role, 0) + 1
            if role == "project_manager" and LoopSafeAdapter._role_calls[role] == 1:
                return AgentResponse(
                    success=True,
                    output=json.dumps(
                        {
                            "action": "message",
                            "to_role": "software_developer",
                            "message": "Start implementation.",
                        }
                    ),
                )
            if role == "project_manager":
                return AgentResponse(
                    success=True,
                    output=json.dumps(
                        {
                            "action": "finalize",
                            "final_response": "Escalation handled by lead.",
                        }
                    ),
                )
            return AgentResponse(
                success=True,
                output=json.dumps(
                    {
                        "action": "message",
                        "to_role": "software_developer",
                        "message": "Still implementing.",
                    }
                ),
            )

    def fake_resolver(self, agent_name, agent_config):
        if agent_config.get("type") == "loop-safe":
            return LoopSafeAdapter
        return None

    monkeypatch.setattr(AgenticTeamEngine, "_resolve_adapter_class", fake_resolver)
    config_file = _write_config(
        tmp_path,
        {
            "agents": {"shared-agent": {"type": "loop-safe", "enabled": True}},
            "settings": {"agentic_team": {"repeat_route_limit": 2}},
            "agentic_team": {
                "lead_role": "project_manager",
                "max_turns": 6,
                "roles": {
                    "project_manager": {"agent": "shared-agent"},
                    "software_architect": {"agent": "shared-agent"},
                    "software_developer": {"agent": "shared-agent"},
                    "qa_engineer": {"agent": "shared-agent"},
                    "devops_engineer": {"agent": "shared-agent"},
                },
            },
        },
    )

    engine = AgenticTeamEngine(config_path=str(config_file))
    result = engine.execute_task("Do work", max_turns=6)
    steps = result["iterations"][0]["steps"]

    assert result["success"] is True
    assert result["stats"]["lead_escalation_count"] >= 1
    assert any(
        step["from_role"] == "software_developer"
        and step["to_role"] == "project_manager"
        and "Repetition detected" in step["message"]
        for step in steps
    )
