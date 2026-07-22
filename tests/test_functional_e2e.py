"""
Functional and end-to-end tests for production readiness.

Includes:
- Real CLI tool availability and invocation (marked @slow)
- Full Orchestrator.execute_task() through all code paths
- Full AgenticTeamEngine.execute_task() with mocked adapters
- UI backend API validation, session concurrency, config endpoints
- Health check platform-independence
- History file truncation
"""

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from orchestrator.adapters.base import AgentCapability, AgentResponse, BaseAdapter

# ============================================================================
# Helpers
# ============================================================================


class StubAdapter(BaseAdapter):
    """Deterministic adapter for E2E testing."""

    def __init__(self, config, *, output="stub output", success=True):
        # Bypass real CLICommunicator init
        self.config = config
        self.name = config.get("name", "stub")
        self.command = config.get("command", "echo")
        self.endpoint = ""
        self.enabled = True
        self.timeout = 10
        self.cli_communicator = None
        self.cli_pattern = {"method": "arg", "supports_workspace": False}
        self.communication_method = "arg"
        self._output = output
        self._success = success
        import logging

        self.logger = logging.getLogger(f"adapter.{self.name}")

    def get_capabilities(self):
        return [AgentCapability.IMPLEMENTATION, AgentCapability.CODE_REVIEW]

    def execute_task(self, task, context):
        return AgentResponse(success=self._success, output=self._output)

    def is_available(self):
        return True


# ============================================================================
# 1. Real CLI tool functional tests (marked slow/integration)
# ============================================================================


@pytest.mark.slow
@pytest.mark.integration
class TestRealCLITools:
    """Tests that verify real CLI tools are accessible on this machine."""

    def test_claude_is_available(self):
        """Claude CLI should be found by the adapter."""
        from orchestrator.adapters.claude_adapter import ClaudeAdapter

        config = {"name": "claude", "enabled": True, "command": "claude"}
        adapter = ClaudeAdapter(config)
        assert adapter.is_available(), "claude CLI not found in PATH"

    def test_codex_is_available(self):
        """Codex CLI should be found by the adapter."""
        from orchestrator.adapters.codex_adapter import CodexAdapter

        config = {"name": "codex", "enabled": True, "command": "codex"}
        adapter = CodexAdapter(config)
        assert adapter.is_available(), "codex CLI not found in PATH"

    def test_gemini_is_available(self):
        """Gemini CLI should be found by the adapter."""
        from orchestrator.adapters.gemini_adapter import GeminiAdapter

        config = {"name": "gemini", "enabled": True, "command": "gemini"}
        adapter = GeminiAdapter(config)
        assert adapter.is_available(), "gemini CLI not found in PATH"

    def test_health_check_finds_claude(self):
        """Platform-independent health check should find claude."""
        from orchestrator.observability.health import HealthChecker

        checker = HealthChecker()
        result = checker.check_agent_availability("claude", "claude")
        assert result.status.value in ("healthy", "degraded")

    def test_health_check_uses_shutil_which(self):
        """Health check should use shutil.which, not subprocess which."""
        import shutil as _shutil

        from orchestrator.observability.health import HealthChecker

        checker = HealthChecker()
        with patch.object(_shutil, "which", return_value="/usr/bin/echo") as mock_which:
            result = checker.check_agent_availability("test", "echo")
            mock_which.assert_called_once_with("echo")
            assert "available" in result.message


# ============================================================================
# 2. Orchestrator.execute_task() end-to-end paths
# ============================================================================


class TestOrchestratorE2E:
    """Full execution path tests through the real Orchestrator."""

    def _make_orchestrator(self, adapters, workflow_config=None):
        """Create orchestrator with injected adapters."""
        from orchestrator.core.engine import Orchestrator

        with patch.object(Orchestrator, "_initialize_adapters"):
            with patch.object(Orchestrator, "_resolve_offline_mode", return_value=False):
                orch = Orchestrator.__new__(Orchestrator)
                import logging

                orch.logger = logging.getLogger("test")
                orch.config = {
                    "agents": {},
                    "workflows": workflow_config
                    or {
                        "default": [
                            {"agent": "impl", "task": "implement"},
                            {"agent": "rev", "task": "review"},
                        ],
                    },
                    "settings": {"max_iterations": 2, "output_dir": "./output"},
                }
                orch.force_offline = False
                orch.is_offline_mode = False
                orch.adapters = adapters
                from orchestrator.core.task_manager import TaskManager
                from orchestrator.core.workflow import WorkflowEngine
                from orchestrator.resilience.fallback import FallbackManager
                from orchestrator.resilience.offline import OfflineDetector

                orch.workflow_engine = WorkflowEngine()
                orch.task_manager = TaskManager()
                orch.fallback_manager = FallbackManager(orch.config, logger=orch.logger)
                orch.offline_detector = OfflineDetector()
                orch.workspace_dir = None
                orch.session_dir = None
                return orch

    def test_execute_task_full_workflow(self):
        """Successful 2-step workflow should produce valid results."""
        adapters = {
            "impl": StubAdapter({"name": "impl"}, output="implemented code"),
            "rev": StubAdapter({"name": "rev"}, output="looks good, no issues"),
        }
        orch = self._make_orchestrator(adapters)
        result = orch.execute_task("build a calculator", "default", max_iterations=1)

        assert result["task"] == "build a calculator"
        assert result["workflow"] == "default"
        assert len(result["iterations"]) == 1
        steps = result["iterations"][0]["steps"]
        assert len(steps) == 2
        assert steps[0]["agent"] == "impl"
        assert steps[1]["agent"] == "rev"
        assert result["success"] is True

    def test_execute_task_missing_workflow_raises(self):
        """Requesting nonexistent workflow should raise ValueError."""
        orch = self._make_orchestrator({})
        with pytest.raises(ValueError, match="not found"):
            orch.execute_task("test", "nonexistent_workflow")

    def test_execute_task_no_available_agents_raises(self):
        """Workflow with no available agents should raise ValueError."""
        orch = self._make_orchestrator({})
        with pytest.raises(ValueError, match="no executable steps"):
            orch.execute_task("test", "default")

    def test_execute_task_multi_iteration_stops_on_success(self):
        """Should stop iterating when review has minimal feedback."""
        adapters = {
            "impl": StubAdapter({"name": "impl"}, output="clean code"),
            "rev": StubAdapter({"name": "rev"}, output="perfect"),
        }
        orch = self._make_orchestrator(adapters)
        result = orch.execute_task("test", "default", max_iterations=5)

        # Should stop after 1 iteration since review has no suggestions
        assert len(result["iterations"]) == 1
        assert result["success"] is True

    def test_execute_task_handles_step_exception(self):
        """If adapter raises, step should be recorded as failed."""

        class FailAdapter(StubAdapter):
            def execute_task(self, task, context):
                raise RuntimeError("boom")

        adapters = {
            "impl": FailAdapter({"name": "impl"}),
            "rev": StubAdapter({"name": "rev"}),
        }
        orch = self._make_orchestrator(adapters)
        result = orch.execute_task("test", "default", max_iterations=1)

        steps = result["iterations"][0]["steps"]
        assert steps[0]["success"] is False
        assert "boom" in steps[0]["error"]

    def test_execute_task_with_fallback(self):
        """Fallback should activate when primary fails with transient error."""

        class ConnFailAdapter(StubAdapter):
            def execute_task(self, task, context):
                raise ConnectionError("network down")

        adapters = {
            "impl": ConnFailAdapter({"name": "impl"}),
            "rev": StubAdapter({"name": "rev"}),
            "local": StubAdapter({"name": "local"}, output="local result"),
        }
        orch = self._make_orchestrator(
            adapters,
            workflow_config={
                "default": [
                    {"agent": "impl", "task": "implement", "fallback": "local"},
                    {"agent": "rev", "task": "review"},
                ],
            },
        )
        orch.fallback_manager = MagicMock()
        orch.fallback_manager.execute_with_fallback.return_value = (
            "local",
            AgentResponse(success=True, output="local result"),
            "impl",
        )

        result = orch.execute_task("test", "default", max_iterations=1)
        steps = result["iterations"][0]["steps"]
        assert steps[0]["agent"] == "local"
        assert steps[0]["fallback_from"] == "impl"


# ============================================================================
# 3. AgenticTeamEngine end-to-end
# ============================================================================


class TestAgenticTeamE2E:
    """Full execution tests through AgenticTeamEngine."""

    def _make_engine(self, responses):
        """Create engine with scripted adapter responses."""
        from agentic_team.engine import AgenticTeamEngine

        call_idx = [0]

        class ScriptedAdapter(StubAdapter):
            def execute_task(self, task, context):
                idx = min(call_idx[0], len(responses) - 1)
                call_idx[0] += 1
                return AgentResponse(success=True, output=responses[idx])

        with patch.object(AgenticTeamEngine, "_initialize_adapters"):
            with patch.object(AgenticTeamEngine, "_resolve_offline_mode", return_value=False):
                engine = AgenticTeamEngine.__new__(AgenticTeamEngine)
                import logging

                from agentic_team.decision_parser import DecisionParser
                from orchestrator.resilience.fallback import FallbackManager
                from orchestrator.resilience.offline import OfflineDetector

                engine.logger = logging.getLogger("test_agentic")
                engine.force_offline = False
                engine.offline_detector = OfflineDetector()
                engine.decision_parser = DecisionParser()
                engine.config_path = Path("config/agents.yaml")
                engine.config = {"settings": {}}
                engine.is_offline_mode = False
                engine.adapters = {"stub": ScriptedAdapter({"name": "stub"})}
                engine.fallback_manager = FallbackManager({}, logger=engine.logger)
                return engine

    def test_full_team_execution_with_finalize(self):
        """Team should route messages and finalize through lead."""
        responses = [
            # Turn 1: PM sends to dev
            json.dumps(
                {"action": "message", "to_role": "software_developer", "message": "implement it"}
            ),
            # Turn 2: Dev sends to PM
            json.dumps(
                {"action": "message", "to_role": "project_manager", "message": "done implementing"}
            ),
            # Turn 3: PM finalizes
            json.dumps(
                {"action": "finalize", "final_response": "All done!", "message": "delivering"}
            ),
        ]
        engine = self._make_engine(responses)
        result = engine.execute_task("build a thing", max_turns=10)

        assert result["success"] is True
        assert result["final_output"] == "All done!"
        assert result["termination_reason"] == "lead_finalize"
        assert result["stats"]["turns_executed"] == 3

    def test_max_turns_without_finalize(self):
        """Reaching max_turns without finalize should produce fallback output."""
        responses = [
            json.dumps(
                {"action": "message", "to_role": "software_developer", "message": "do work"}
            ),
            json.dumps({"action": "message", "to_role": "project_manager", "message": "done"}),
        ]
        engine = self._make_engine(responses)
        result = engine.execute_task("build", max_turns=2)

        assert result["success"] is False
        assert result["termination_reason"] == "max_turns_reached_without_finalize"
        assert "max turns" in result["final_output"].lower()

    def test_turn_callback_receives_all_turns(self):
        """Turn callback should fire for each turn."""
        responses = [
            json.dumps({"action": "finalize", "final_response": "done", "message": "done"}),
        ]
        engine = self._make_engine(responses)
        turns = []
        result = engine.execute_task("test", max_turns=5, turn_callback=turns.append)

        assert len(turns) >= 1
        assert turns[0]["turn"] == 1
        assert "execution_id" in turns[0]

    def test_empty_task_raises(self):
        """Empty task should raise ValueError."""
        engine = self._make_engine([])
        with pytest.raises(ValueError, match="required"):
            engine.execute_task("", max_turns=1)


# ============================================================================
# 4. UI Backend API functional tests
# ============================================================================


class TestUIBackendAPI:
    """Functional tests for the orchestrator web UI backend."""

    @pytest.fixture
    def client(self):
        import orchestrator.ui.app as ui_app

        ui_app.orchestrator = MagicMock()
        ui_app.orchestrator.adapters = {}
        ui_app.orchestrator.config = {"agents": {}, "workflows": {}, "settings": {}}
        ui_app.app.config["TESTING"] = True
        with ui_app.app.test_client() as c:
            yield c

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json["status"] == "healthy"

    def test_readiness_returns_503_when_no_orchestrator(self, client):
        import orchestrator.ui.app as ui_app

        ui_app.orchestrator = None
        resp = client.get("/ready")
        assert resp.status_code == 503

    def test_execute_rejects_missing_task(self, client):
        resp = client.post("/api/execute", json={})
        assert resp.status_code == 400
        assert "required" in resp.json["error"].lower()

    def test_execute_rejects_empty_task(self, client):
        resp = client.post("/api/execute", json={"task": ""})
        assert resp.status_code == 400

    def test_get_agents_returns_list(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert "agents" in resp.json

    def test_get_workflows_returns_list(self, client):
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        assert "workflows" in resp.json

    def test_config_get_returns_404_when_missing(self, client):
        import orchestrator.ui.app as ui_app

        with patch.object(ui_app, "_config_path", return_value=Path("/nonexistent/agents.yaml")):
            resp = client.get("/api/config")
            assert resp.status_code == 404

    def test_config_put_rejects_invalid_yaml(self, client):
        resp = client.put(
            "/api/config",
            json={"content": "not: valid: yaml: ["},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_config_put_rejects_missing_sections(self, client):
        resp = client.put(
            "/api/config",
            json={"config": {"agents": {}}},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "Missing required section" in resp.json["error"]

    def test_path_traversal_blocked(self, client):
        resp = client.get("/api/files/../../etc/passwd")
        assert resp.status_code in (403, 404)

    def test_conversation_clear(self, client):
        resp = client.post("/api/conversation/clear", json={"client_id": "test123"})
        assert resp.status_code == 200
        assert resp.json["client_id"] == "test123"

    def test_status_returns_session(self, client):
        resp = client.get("/api/status?client_id=test")
        assert resp.status_code == 200
        assert "status" in resp.json

    def test_metrics_returns_prometheus_format(self, client):
        import orchestrator.ui.app as ui_app

        ui_app.orchestrator = MagicMock()
        ui_app.orchestrator.adapters = {"a": MagicMock(is_available=lambda: True)}
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "ai_orchestrator_up 1" in resp.data.decode()


class TestAgenticUIBackendAPI:
    """Functional tests for the agentic team web UI backend."""

    @pytest.fixture
    def client(self):
        import agentic_team.ui.app as ag_app

        ag_app.engine = MagicMock()
        ag_app.engine.get_available_agents.return_value = ["claude"]
        ag_app.engine.get_team_config.return_value = {
            "roles": {},
            "lead_role": "pm",
            "max_turns": 12,
        }
        ag_app.engine.get_runtime_status.return_value = {}
        ag_app.app.config["TESTING"] = True
        with ag_app.app.test_client() as c:
            yield c

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_team_config_endpoint(self, client):
        resp = client.get("/api/team/config")
        assert resp.status_code == 200
        assert "team" in resp.json

    def test_execute_rejects_non_string_task(self, client):
        resp = client.post("/api/execute", json={"task": 12345})
        assert resp.status_code == 400

    def test_execute_rejects_empty(self, client):
        resp = client.post("/api/execute", json={})
        assert resp.status_code == 400

    def test_status_returns_client_id(self, client):
        resp = client.get("/api/status?client_id=abc")
        assert resp.status_code == 200
        assert resp.json["client_id"] == "abc"


# ============================================================================
# 5. Session concurrency
# ============================================================================


class TestSessionIsolation:
    """Verify sessions don't leak across clients."""

    def test_concurrent_session_writes(self):
        import orchestrator.ui.app as ui_app

        ui_app.orchestrator = MagicMock()
        ui_app.orchestrator.adapters = {}
        ui_app.orchestrator.config = {"agents": {}, "workflows": {}, "settings": {}}

        errors = []

        def clear_session(cid):
            try:
                with ui_app.app.test_client() as c:
                    resp = c.post("/api/conversation/clear", json={"client_id": cid})
                    assert resp.status_code == 200
                    assert resp.json["client_id"] == cid
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=clear_session, args=(f"client_{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"


# ============================================================================
# 6. History truncation
# ============================================================================


class TestHistoryTruncation:
    """Verify the history file truncation fix."""

    def test_truncate_large_history(self):
        """Large history file should be truncated to MAX_HISTORY_LINES."""
        from orchestrator.cli.shell import InteractiveShell

        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.txt"
            # Write 50000 lines
            with open(history_file, "w") as f:
                for i in range(50000):
                    f.write(f"command_{i}\n")
            assert history_file.stat().st_size > 512 * 1024

            InteractiveShell._truncate_history_file(history_file, 1000)

            lines = history_file.read_text().splitlines()
            assert len(lines) <= 1000
            assert "command_49999" in lines[-1]

    def test_small_history_not_truncated(self):
        """Small history file should not be modified."""
        from orchestrator.cli.shell import InteractiveShell

        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.txt"
            with open(history_file, "w") as f:
                for i in range(10):
                    f.write(f"cmd_{i}\n")
            original_size = history_file.stat().st_size

            InteractiveShell._truncate_history_file(history_file, 1000)
            assert history_file.stat().st_size == original_size

    def test_missing_history_no_error(self):
        """Truncating nonexistent file should not raise."""
        from orchestrator.cli.shell import InteractiveShell

        InteractiveShell._truncate_history_file(Path("/nonexistent/history.txt"), 1000)


# ============================================================================
# 7. Config manager end-to-end
# ============================================================================


class TestConfigManagerE2E:
    def test_full_config_load_validate_cycle(self):
        """ConfigManager should load YAML and validate."""
        from orchestrator.infra.config_manager import ConfigManager

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("""
agents:
  test:
    enabled: true
    command: echo
workflows:
  default:
    - agent: test
      task: implement
settings:
  max_iterations: 2
""")
            tmpname = f.name
        try:
            cm = ConfigManager(config_file=Path(tmpname))
            assert cm.validate() is True
            assert cm.get_agent_config("test") is not None
            assert cm.get_workflow_config("default") is not None
        finally:
            if os.path.exists(tmpname):
                os.unlink(tmpname)


# ============================================================================
# 8. Fallback manager edge cases
# ============================================================================


class TestFallbackManagerE2E:
    def test_fallback_chain_when_both_fail(self):
        """When primary and fallback both fail, error includes both."""
        from orchestrator.resilience.fallback import FallbackManager

        class FailAdapter:
            def execute_task(self, task, context):
                raise ConnectionError("down")

        fm = FallbackManager(
            {"settings": {"fallback": {"enabled": True, "map": {"primary": "backup"}}}}
        )
        agent, resp, fb = fm.execute_with_fallback(
            primary_agent="primary",
            adapters={"primary": FailAdapter(), "backup": FailAdapter()},
            task="test",
            context={},
        )
        assert resp.success is False
        assert "Primary failed" in resp.error
        assert "fallback" in resp.error

    def test_no_fallback_when_error_not_transient(self):
        """Non-transient errors should not trigger fallback."""
        from orchestrator.resilience.fallback import FallbackManager

        fm = FallbackManager({"settings": {"fallback": {"enabled": True, "map": {"a": "b"}}}})
        mock_primary = MagicMock()
        mock_primary.execute_task.return_value = AgentResponse(
            success=False, output="", error="syntax error in code"
        )
        mock_backup = MagicMock()

        agent, resp, fb = fm.execute_with_fallback(
            primary_agent="a",
            adapters={"a": mock_primary, "b": mock_backup},
            task="test",
            context={},
        )
        # Should NOT have fallen back
        assert agent == "a"
        assert fb is None
        mock_backup.execute_task.assert_not_called()


# ============================================================================
# 9. Orchestrator - exhausted iterations still mark success
# ============================================================================


class TestOrchestratorIterationExhaustion:
    """Verify fix: when all iterations exhaust but steps pass, success=True."""

    def _make_orchestrator(self, adapters, workflow_config):
        from orchestrator.core.engine import Orchestrator

        with patch.object(Orchestrator, "_initialize_adapters"):
            with patch.object(Orchestrator, "_resolve_offline_mode", return_value=False):
                orch = Orchestrator.__new__(Orchestrator)
                import logging

                from orchestrator.core.task_manager import TaskManager
                from orchestrator.core.workflow import WorkflowEngine
                from orchestrator.resilience.fallback import FallbackManager
                from orchestrator.resilience.offline import OfflineDetector

                orch.logger = logging.getLogger("test")
                orch.config = {
                    "agents": {},
                    "workflows": workflow_config,
                    "settings": {"max_iterations": 2, "output_dir": "./output"},
                }
                orch.force_offline = False
                orch.is_offline_mode = False
                orch.adapters = adapters
                orch.workflow_engine = WorkflowEngine()
                orch.task_manager = TaskManager()
                orch.fallback_manager = FallbackManager(orch.config, logger=orch.logger)
                orch.offline_detector = OfflineDetector()
                orch.workspace_dir = None
                orch.session_dir = None
                return orch

    def test_max_iterations_exhausted_all_steps_succeed_marks_success(self):
        """When review always has many suggestions but all steps succeed,
        exhausting max_iterations should still yield success=True."""

        class VerboseReviewer(StubAdapter):
            def execute_task(self, task, context):
                return AgentResponse(
                    success=True,
                    output="many issues found",
                    suggestions=["fix A", "fix B", "fix C", "fix D", "fix E"],
                )

        adapters = {
            "impl": StubAdapter({"name": "impl"}, output="code"),
            "rev": VerboseReviewer({"name": "rev"}),
        }
        orch = self._make_orchestrator(
            adapters,
            {
                "default": [
                    {"agent": "impl", "task": "implement"},
                    {"agent": "rev", "task": "review"},
                ],
            },
        )
        result = orch.execute_task("test", "default", max_iterations=2)

        assert len(result["iterations"]) == 2
        # Key assertion: success should be True since all steps succeeded
        assert result["success"] is True
        assert result["final_output"] is not None

    def test_failed_step_means_failure(self):
        """If a step fails in last iteration, success should be False."""
        adapters = {
            "impl": StubAdapter({"name": "impl"}, output="code", success=False),
        }
        orch = self._make_orchestrator(
            adapters,
            {
                "default": [{"agent": "impl", "task": "implement"}],
            },
        )
        result = orch.execute_task("test", "default", max_iterations=1)
        assert result["success"] is False


# ============================================================================
# 10. Orchestrator - error step has complete dict keys
# ============================================================================


class TestOrchestratorStepErrorKeys:
    """Verify fix: exception handler includes all expected step_result keys."""

    def test_exception_step_has_all_keys(self):
        class RaisingAdapter(StubAdapter):
            def execute_task(self, task, context):
                raise RuntimeError("adapter exploded")

        adapters = {"bad": RaisingAdapter({"name": "bad"})}

        from orchestrator.core.engine import Orchestrator

        with patch.object(Orchestrator, "_initialize_adapters"):
            with patch.object(Orchestrator, "_resolve_offline_mode", return_value=False):
                orch = Orchestrator.__new__(Orchestrator)
                import logging

                from orchestrator.core.task_manager import TaskManager
                from orchestrator.core.workflow import WorkflowEngine
                from orchestrator.resilience.fallback import FallbackManager
                from orchestrator.resilience.offline import OfflineDetector

                orch.logger = logging.getLogger("test")
                orch.config = {
                    "agents": {},
                    "workflows": {"w": [{"agent": "bad", "task": "implement"}]},
                    "settings": {"max_iterations": 1, "output_dir": "./output"},
                }
                orch.force_offline = False
                orch.is_offline_mode = False
                orch.adapters = adapters
                orch.workflow_engine = WorkflowEngine()
                orch.task_manager = TaskManager()
                orch.fallback_manager = FallbackManager(orch.config, logger=orch.logger)
                orch.offline_detector = OfflineDetector()
                orch.workspace_dir = None
                orch.session_dir = None

        result = orch.execute_task("test", "w", max_iterations=1)
        step = result["iterations"][0]["steps"][0]

        # All expected keys must exist
        for key in ("agent", "task", "success", "output", "error", "files_modified", "suggestions"):
            assert key in step, f"Missing key: {key}"
        assert step["success"] is False
        assert "exploded" in step["error"]
        assert step["output"] == ""
        assert step["files_modified"] == []
        assert step["suggestions"] == []


# ============================================================================
# 11. Agentic Team - complete flow with context propagation
# ============================================================================


class TestAgenticTeamCompleteFlow:
    """Test the full agentic team lifecycle with context tracking."""

    def _make_engine(self, responses):
        from agentic_team.decision_parser import DecisionParser
        from agentic_team.engine import AgenticTeamEngine
        from orchestrator.resilience.fallback import FallbackManager
        from orchestrator.resilience.offline import OfflineDetector

        call_idx = [0]

        class ScriptedAdapter(StubAdapter):
            def execute_task(self, task, context):
                idx = min(call_idx[0], len(responses) - 1)
                call_idx[0] += 1
                return AgentResponse(success=True, output=responses[idx])

        with patch.object(AgenticTeamEngine, "_initialize_adapters"):
            with patch.object(AgenticTeamEngine, "_resolve_offline_mode", return_value=False):
                engine = AgenticTeamEngine.__new__(AgenticTeamEngine)
                import logging

                engine.logger = logging.getLogger("test_agentic")
                engine.force_offline = False
                engine.offline_detector = OfflineDetector()
                engine.decision_parser = DecisionParser()
                engine.config_path = Path("config/agents.yaml")
                engine.config = {"settings": {}}
                engine.is_offline_mode = False
                engine.adapters = {"stub": ScriptedAdapter({"name": "stub"})}
                engine.fallback_manager = FallbackManager({}, logger=engine.logger)
                return engine

    def test_multi_hop_routing_then_finalize(self):
        """PM -> Architect -> Developer -> QA -> PM -> finalize."""
        responses = [
            json.dumps(
                {
                    "action": "message",
                    "to_role": "software_architect",
                    "message": "Design the architecture",
                }
            ),
            json.dumps(
                {
                    "action": "message",
                    "to_role": "software_developer",
                    "message": "Here is the design, implement it",
                }
            ),
            json.dumps(
                {
                    "action": "message",
                    "to_role": "qa_engineer",
                    "message": "Code implemented, please test",
                }
            ),
            json.dumps(
                {
                    "action": "message",
                    "to_role": "project_manager",
                    "message": "All tests pass, ready to deliver",
                }
            ),
            json.dumps(
                {
                    "action": "finalize",
                    "final_response": "Feature complete with tests",
                    "message": "Delivering to user",
                }
            ),
        ]
        engine = self._make_engine(responses)
        result = engine.execute_task("Build a REST API", max_turns=10)

        assert result["success"] is True
        assert result["termination_reason"] == "lead_finalize"
        assert result["final_output"] == "Feature complete with tests"
        assert result["stats"]["turns_executed"] == 5

        # Verify routing
        steps = result["iterations"][0]["steps"]
        assert steps[0]["from_role"] == "project_manager"
        assert steps[0]["to_role"] == "software_architect"
        assert steps[1]["from_role"] == "software_architect"
        assert steps[1]["to_role"] == "software_developer"
        assert steps[4]["action"] == "finalize"

    def test_result_structure_is_complete(self):
        """Result dict should have all required top-level fields."""
        responses = [
            json.dumps({"action": "finalize", "final_response": "Done", "message": "Delivering"}),
        ]
        engine = self._make_engine(responses)
        result = engine.execute_task("test task", max_turns=5)

        required_keys = {
            "task",
            "engine",
            "execution_id",
            "started_at",
            "completed_at",
            "duration_ms",
            "termination_reason",
            "iterations",
            "final_output",
            "success",
            "offline_mode",
            "stats",
            "team",
        }
        assert required_keys.issubset(set(result.keys()))
        assert result["engine"] == "agentic_team"
        assert isinstance(result["execution_id"], str) and len(result["execution_id"]) > 0
        assert result["duration_ms"] >= 0
        assert isinstance(result["stats"]["turns_executed"], int)
        assert isinstance(result["team"]["roles"], dict)

    def test_failed_agent_routes_to_lead(self):
        """When an agent fails, message should route to lead with error."""
        from agentic_team.decision_parser import DecisionParser
        from agentic_team.engine import AgenticTeamEngine
        from orchestrator.resilience.fallback import FallbackManager
        from orchestrator.resilience.offline import OfflineDetector

        call_count = [0]

        class FailThenSucceed(StubAdapter):
            def execute_task(self, task, context):
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call (PM delegates) succeeds
                    return AgentResponse(
                        success=True,
                        output=json.dumps(
                            {
                                "action": "message",
                                "to_role": "software_developer",
                                "message": "implement it",
                            }
                        ),
                    )
                elif call_count[0] == 2:
                    # Developer fails
                    return AgentResponse(success=False, output="", error="compilation error")
                else:
                    # PM gets error, finalizes
                    return AgentResponse(
                        success=True,
                        output=json.dumps(
                            {
                                "action": "finalize",
                                "final_response": "Could not complete due to error",
                                "message": "done",
                            }
                        ),
                    )

        with patch.object(AgenticTeamEngine, "_initialize_adapters"):
            with patch.object(AgenticTeamEngine, "_resolve_offline_mode", return_value=False):
                engine = AgenticTeamEngine.__new__(AgenticTeamEngine)
                import logging

                engine.logger = logging.getLogger("test")
                engine.force_offline = False
                engine.offline_detector = OfflineDetector()
                engine.decision_parser = DecisionParser()
                engine.config_path = Path("config/agents.yaml")
                engine.config = {"settings": {}}
                engine.is_offline_mode = False
                engine.adapters = {"stub": FailThenSucceed({"name": "stub"})}
                engine.fallback_manager = FallbackManager({}, logger=engine.logger)

        result = engine.execute_task("build feature", max_turns=10)
        steps = result["iterations"][0]["steps"]

        # Turn 2 should show failure routed to lead
        failed_step = steps[1]
        assert failed_step["success"] is False
        assert failed_step["to_role"] == "project_manager"
        assert "compilation error" in failed_step["message"]


# ============================================================================
# 12. UI Backend - full execute flow simulation
# ============================================================================


class TestUIExecuteFlow:
    """Test the /api/execute endpoint creates a background task and updates session."""

    def test_execute_starts_and_updates_session(self):
        import orchestrator.ui.app as ui_app

        mock_orch = MagicMock()
        mock_orch.adapters = {"claude": MagicMock(is_available=lambda: True)}
        mock_orch.config = {"agents": {}, "workflows": {"default": []}, "settings": {}}
        mock_orch.execute_task.return_value = {
            "success": True,
            "iterations": [{"steps": [], "final_output": "done"}],
            "final_output": "done",
        }
        ui_app.orchestrator = mock_orch

        client = ui_app.app.test_client()
        resp = client.post(
            "/api/execute",
            json={
                "task": "build a calculator",
                "workflow": "default",
                "client_id": "test_e2e",
            },
        )
        assert resp.status_code == 200
        data = resp.json
        assert data["message"] == "Task started"
        assert data["client_id"] == "test_e2e"
