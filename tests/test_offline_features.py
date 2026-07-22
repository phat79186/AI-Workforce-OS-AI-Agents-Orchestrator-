"""Tests for offline/local model orchestration features."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import Mock, patch

import httpx
import pytest
import yaml

from orchestrator.adapters import (
    AgentResponse,
    BaseAdapter,
    ClaudeAdapter,
    CodexAdapter,
    CopilotAdapter,
    GeminiAdapter,
    LlamaCppAdapter,
    OllamaAdapter,
)
from orchestrator.core.engine import Orchestrator
from orchestrator.resilience.fallback import FallbackManager
from orchestrator.resilience.offline import OfflineDetector


def _write_config(tmp_path, config_data: dict[str, Any]):
    config_file = tmp_path / "offline_test_config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    return config_file


def test_custom_named_ollama_agent_resolves_by_type(tmp_path):
    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "my-custom-llama": {
                    "type": "ollama",
                    "enabled": True,
                    "offline": True,
                    "endpoint": "http://localhost:11434",
                    "model": "codellama:13b",
                }
            },
            "workflows": {"default": [{"agent": "my-custom-llama", "task": "implement"}]},
            "settings": {},
        },
    )

    with patch.object(OllamaAdapter, "is_available", return_value=True):
        orchestrator = Orchestrator(config_path=str(config_file))

    assert "my-custom-llama" in orchestrator.adapters
    assert isinstance(orchestrator.adapters["my-custom-llama"], OllamaAdapter)


def test_custom_named_llamacpp_agent_resolves_by_type(tmp_path):
    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "my-local-openai": {
                    "type": "llamacpp",
                    "enabled": True,
                    "offline": True,
                    "endpoint": "http://localhost:8080",
                }
            },
            "workflows": {"default": [{"agent": "my-local-openai", "task": "implement"}]},
            "settings": {},
        },
    )

    with patch.object(LlamaCppAdapter, "is_available", return_value=True):
        orchestrator = Orchestrator(config_path=str(config_file))

    assert "my-local-openai" in orchestrator.adapters
    assert isinstance(orchestrator.adapters["my-local-openai"], LlamaCppAdapter)


def test_force_offline_skips_cloud_agents(tmp_path):
    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "codex": {"type": "cli", "enabled": True, "command": "codex"},
                "local-code": {
                    "type": "ollama",
                    "enabled": True,
                    "offline": True,
                    "endpoint": "http://localhost:11434",
                },
            },
            "workflows": {"default": [{"agent": "local-code", "task": "implement"}]},
            "settings": {},
        },
    )

    with patch(
        "orchestrator.adapters.codex_adapter.CodexAdapter.is_available", return_value=True
    ), patch.object(OllamaAdapter, "is_available", return_value=True):
        orchestrator = Orchestrator(config_path=str(config_file), force_offline=True)

    assert "local-code" in orchestrator.adapters
    assert "codex" not in orchestrator.adapters


def test_workflow_dict_steps_and_role_mapping(tmp_path):
    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "local-code": {
                    "type": "ollama",
                    "enabled": True,
                    "offline": True,
                    "endpoint": "http://localhost:11434",
                },
                "local-instruct": {
                    "type": "ollama",
                    "enabled": True,
                    "offline": True,
                    "endpoint": "http://localhost:11434",
                },
            },
            "workflows": {
                "offline-default": {
                    "description": "local only",
                    "steps": [
                        {"agent": "local-code", "role": "implementer"},
                        {"agent": "local-instruct", "role": "reviewer"},
                    ],
                }
            },
            "settings": {},
        },
    )

    with patch.object(OllamaAdapter, "is_available", return_value=True):
        orchestrator = Orchestrator(config_path=str(config_file))

    workflow_steps_config = orchestrator._extract_workflow_steps(
        orchestrator.config["workflows"]["offline-default"]
    )
    steps = orchestrator._build_workflow_steps(workflow_steps_config)
    assert [step.task_type for step in steps] == ["implement", "review"]


def test_fallback_manager_recovers_on_connection_error():
    fallback_manager = FallbackManager(
        {"settings": {"fallback": {"enabled": True, "map": {"cloud-reviewer": "local-reviewer"}}}}
    )

    cloud_adapter = Mock(spec=BaseAdapter)
    cloud_adapter.execute_task.return_value = AgentResponse(
        success=False, output="", error="connection timed out"
    )

    local_adapter = Mock(spec=BaseAdapter)
    local_adapter.execute_task.return_value = AgentResponse(success=True, output="local review")

    agent_used, response, fallback_from = fallback_manager.execute_with_fallback(
        primary_agent="cloud-reviewer",
        adapters={"cloud-reviewer": cloud_adapter, "local-reviewer": local_adapter},
        task="Review code",
        context={"role": "review"},
    )

    assert agent_used == "local-reviewer"
    assert fallback_from == "cloud-reviewer"
    assert response.success is True


def test_offline_detector_caches_checks(monkeypatch):
    detector = OfflineDetector(check_interval=9999)
    check_count = {"value": 0}

    def fake_check():
        check_count["value"] += 1
        return True

    monkeypatch.setattr(detector, "_check_connectivity", fake_check)

    assert detector.is_offline() is False
    assert detector.is_offline() is False
    assert check_count["value"] == 1

    assert detector.is_offline(force_refresh=True) is False
    assert check_count["value"] == 2


def test_type_cli_command_alias_maps_to_known_adapter(tmp_path):
    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "my-reviewer": {
                    "type": "cli",
                    "enabled": True,
                    "command": "gemini-cli",
                }
            },
            "workflows": {"default": [{"agent": "my-reviewer", "task": "review"}]},
            "settings": {},
        },
    )

    with patch(
        "orchestrator.adapters.gemini_adapter.GeminiAdapter.is_available", return_value=True
    ):
        orchestrator = Orchestrator(config_path=str(config_file))

    assert "my-reviewer" in orchestrator.adapters


@pytest.mark.parametrize(
    "agent_name,command,expected_class,patch_target",
    [
        (
            "custom-coder",
            "codex",
            CodexAdapter,
            "orchestrator.adapters.codex_adapter.CodexAdapter.is_available",
        ),
        (
            "custom-reviewer",
            "gemini-cli",
            GeminiAdapter,
            "orchestrator.adapters.gemini_adapter.GeminiAdapter.is_available",
        ),
        (
            "custom-refiner",
            "claude",
            ClaudeAdapter,
            "orchestrator.adapters.claude_adapter.ClaudeAdapter.is_available",
        ),
        (
            "custom-suggester",
            "github-copilot-cli",
            CopilotAdapter,
            "orchestrator.adapters.copilot_adapter.CopilotAdapter.is_available",
        ),
    ],
)
def test_type_cli_custom_name_still_maps_core_adapters(
    tmp_path, agent_name, command, expected_class, patch_target
):
    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                agent_name: {
                    "type": "cli",
                    "enabled": True,
                    "command": command,
                }
            },
            "workflows": {"default": [{"agent": agent_name, "task": "implement"}]},
            "settings": {},
        },
    )

    with patch(patch_target, return_value=True):
        orchestrator = Orchestrator(config_path=str(config_file))

    assert agent_name in orchestrator.adapters
    assert isinstance(orchestrator.adapters[agent_name], expected_class)


def test_fallback_manager_handles_fallback_exception():
    fallback_manager = FallbackManager(
        {"settings": {"fallback": {"enabled": True, "map": {"cloud": "local"}}}}
    )

    cloud_adapter = Mock(spec=BaseAdapter)
    cloud_adapter.execute_task.return_value = AgentResponse(
        success=False, output="", error="connection reset by peer"
    )

    local_adapter = Mock(spec=BaseAdapter)
    local_adapter.execute_task.side_effect = RuntimeError("local backend down")

    agent_used, response, fallback_from = fallback_manager.execute_with_fallback(
        primary_agent="cloud",
        adapters={"cloud": cloud_adapter, "local": local_adapter},
        task="Review code",
        context={},
    )

    assert agent_used == "cloud"
    assert fallback_from is None
    assert response.success is False
    assert "fallback 'local' failed" in (response.error or "")


def test_orchestrator_executes_step_level_fallback(tmp_path, monkeypatch):
    class PrimaryAdapter(BaseAdapter):
        def get_capabilities(self):
            return []

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            return AgentResponse(success=False, output="", error="network timeout")

        def is_available(self) -> bool:
            return True

    class BackupAdapter(BaseAdapter):
        def get_capabilities(self):
            return []

        def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
            return AgentResponse(success=True, output="fallback output")

        def is_available(self) -> bool:
            return True

    def fake_resolver(self, agent_name, agent_config):
        agent_type = agent_config.get("type")
        if agent_type == "primary":
            return PrimaryAdapter
        if agent_type == "backup":
            return BackupAdapter
        return None

    monkeypatch.setattr(Orchestrator, "_resolve_adapter_class", fake_resolver)

    config_file = _write_config(
        tmp_path,
        {
            "agents": {
                "cloud-agent": {"type": "primary", "enabled": True, "command": "fake"},
                "local-agent": {"type": "backup", "enabled": True, "offline": True},
            },
            "workflows": {
                "default": [{"agent": "cloud-agent", "task": "review", "fallback": "local-agent"}]
            },
            "settings": {"fallback": {"enabled": True}},
        },
    )

    orchestrator = Orchestrator(config_path=str(config_file))
    result = orchestrator.execute_task("Review this", max_iterations=1)
    step_result = result["iterations"][0]["steps"][0]

    assert step_result["agent"] == "local-agent"
    assert step_result["fallback_from"] == "cloud-agent"
    assert step_result["success"] is True


@pytest.mark.asyncio
async def test_ollama_adapter_async_execute_with_mock_transport(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/generate":
            return httpx.Response(
                200,
                json={"response": "generated", "eval_count": 12, "eval_duration": 1000000},
            )
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        "orchestrator.adapters.ollama_adapter.httpx.AsyncClient", patched_async_client
    )

    adapter = OllamaAdapter(
        {
            "name": "local-code",
            "type": "ollama",
            "endpoint": "http://localhost:11434",
            "model": "codellama:13b",
            "offline": True,
        }
    )

    response = await adapter.execute_task_async("Implement hello world", {"role": "implement"})
    assert response.success is True
    assert response.output == "generated"
    assert response.metadata["model"] == "codellama:13b"


@pytest.mark.asyncio
async def test_llamacpp_adapter_async_execute_with_mock_transport(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/completions":
            return httpx.Response(200, json={"choices": [{"text": "done"}]})
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        "orchestrator.adapters.llama_cpp_adapter.httpx.AsyncClient", patched_async_client
    )

    adapter = LlamaCppAdapter(
        {
            "name": "local-large",
            "type": "llamacpp",
            "endpoint": "http://localhost:8080",
            "offline": True,
        }
    )

    response = await adapter.execute_task_async("Implement hello world", {"role": "implement"})
    assert response.success is True
    assert response.output == "done"
