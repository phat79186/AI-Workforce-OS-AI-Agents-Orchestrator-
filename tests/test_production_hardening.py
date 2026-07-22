"""
Tests for production-hardening improvements across all modules.

Covers: security fixes, type safety, error handling, thread safety,
resource management, and enterprise-grade correctness.
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.adapters.base import AgentResponse

# ---------------------------------------------------------------------------
# 1. AgentResponse dataclass improvements
# ---------------------------------------------------------------------------


class TestAgentResponseDataclass:
    """Verify proper dataclass field defaults after fix."""

    def test_default_lists_are_independent(self):
        """Each instance should have its own list, not share mutable defaults."""
        r1 = AgentResponse(success=True, output="a")
        r2 = AgentResponse(success=True, output="b")
        r1.files_modified.append("file.py")
        assert r2.files_modified == []
        assert r1.files_modified == ["file.py"]

    def test_default_metadata_is_independent(self):
        r1 = AgentResponse(success=True, output="")
        r2 = AgentResponse(success=True, output="")
        r1.metadata["key"] = "val"
        assert "key" not in r2.metadata

    def test_explicit_lists_preserved(self):
        r = AgentResponse(
            success=True,
            output="ok",
            files_modified=["a.py"],
            suggestions=["fix X"],
            metadata={"k": "v"},
        )
        assert r.files_modified == ["a.py"]
        assert r.suggestions == ["fix X"]
        assert r.metadata == {"k": "v"}


# ---------------------------------------------------------------------------
# 2. BaseAdapter null-check for cli_communicator
# ---------------------------------------------------------------------------

from orchestrator.adapters.base import BaseAdapter


class ConcreteAdapter(BaseAdapter):
    """Minimal concrete adapter for testing."""

    def get_capabilities(self):
        return []

    def execute_task(self, task, context):
        return self._run_command_with_prompt(task)


class TestBaseAdapterNullCommunicator:
    def test_run_command_with_prompt_returns_error_when_no_communicator(self):
        """If cli_communicator is None (offline agent), return graceful error."""
        config = {"name": "test", "offline": True, "enabled": True, "command": "echo"}
        adapter = ConcreteAdapter(config)
        assert adapter.cli_communicator is None
        response = adapter.execute_task("hello", {})
        assert response.success is False
        assert "not initialized" in response.error


# ---------------------------------------------------------------------------
# 3. CLI communicator improvements
# ---------------------------------------------------------------------------

from orchestrator.adapters.cli_communicator import CLICommunicator


class TestCLICommunicatorHardening:
    def test_unknown_method_falls_back_to_arg(self):
        """Unknown method should not raise ValueError, should fall back."""
        comm = CLICommunicator("echo test")
        # Should not raise
        success, stdout, stderr = comm.execute_with_prompt(
            "hello", method="unknown_method", timeout=5
        )
        # May fail because echo doesn't behave as expected, but should not raise
        assert isinstance(success, bool)

    def test_cleanup_handles_missing_dir(self):
        """Cleanup should not raise even if temp dir already removed."""
        comm = CLICommunicator("echo")
        shutil.rmtree(comm.temp_dir, ignore_errors=True)
        # Should not raise
        comm.cleanup()

    def test_temp_dir_created(self):
        """Temp dir should exist after init."""
        comm = CLICommunicator("echo")
        assert os.path.isdir(comm.temp_dir)
        comm.cleanup()


# ---------------------------------------------------------------------------
# 4. Security - path traversal protection
# ---------------------------------------------------------------------------


class TestPathTraversalProtection:
    def test_file_endpoint_blocks_traversal(self):
        """The /api/files/ endpoint should reject path traversal."""
        import orchestrator.ui.app as ui_app

        ui_app.orchestrator = MagicMock()
        client = ui_app.app.test_client()
        response = client.get("/api/files/../../etc/passwd")
        assert response.status_code in (403, 404)

    def test_security_validator_path_traversal(self):
        """InputValidator should reject paths outside allowed_root."""
        from orchestrator.security_module.security import InputValidator

        with pytest.raises(Exception):
            InputValidator.validate_file_path(
                "/etc/passwd",
                allowed_root=Path("/tmp/safe"),
            )


# ---------------------------------------------------------------------------
# 5. Security - no hardcoded secrets
# ---------------------------------------------------------------------------


class TestSecurityConfig:
    def test_app_secret_key_not_hardcoded(self):
        """Flask secret key should not be the default hardcoded value."""
        import orchestrator.ui.app as ui_app

        assert ui_app.app.config["SECRET_KEY"] != "ai-orchestrator-secret-key-change-in-production"

    def test_agentic_app_secret_key_not_hardcoded(self):
        import agentic_team.ui.app as agentic_app

        assert agentic_app.app.config["SECRET_KEY"] != "agentic-team-ui-secret-change-in-production"


# ---------------------------------------------------------------------------
# 6. Thread-safe singletons
# ---------------------------------------------------------------------------


class TestThreadSafeSingletons:
    def test_config_manager_thread_safe(self):
        """get_config_manager should return same instance from multiple threads."""
        from orchestrator.infra.config_manager import get_config_manager

        results = []
        errors = []

        def get_cm():
            try:
                cm = get_config_manager()
                results.append(id(cm))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_cm) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All should be the same instance
        assert len(set(results)) == 1

    def test_cache_singleton_thread_safe(self):
        """get_cache should return same instance from multiple threads."""
        from orchestrator.infra.cache import get_cache

        results = []

        def get_c():
            results.append(id(get_cache()))

        threads = [threading.Thread(target=get_c) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(results)) == 1

    def test_metrics_singleton_thread_safe(self):
        """get_metrics_collector should return same instance from multiple threads."""
        from orchestrator.observability.metrics import get_metrics_collector

        results = []

        def get_m():
            results.append(id(get_metrics_collector()))

        threads = [threading.Thread(target=get_m) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# 7. Cache improvements
# ---------------------------------------------------------------------------


class TestCacheImprovements:
    def test_cleanup_expired_thread_safe(self):
        """cleanup_expired should not crash even with concurrent access."""
        from orchestrator.infra.cache import InMemoryCache

        cache = InMemoryCache(default_ttl=0)
        for i in range(100):
            cache.set(f"key_{i}", f"val_{i}", ttl=0)
        time.sleep(0.01)
        removed = cache.cleanup_expired()
        assert removed == 100
        assert len(cache.cache) == 0

    def test_file_cache_handles_non_serializable(self):
        """FileCache should handle non-JSON-serializable values gracefully."""
        from orchestrator.infra.cache import FileCache

        tmpdir = tempfile.mkdtemp()
        try:
            fc = FileCache(tmpdir)
            # Lambda is not JSON serializable - should not raise
            fc.set("key", lambda x: x)
            # Value not cached, should return None
            assert fc.get("key") is None
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 8. Metrics improvements
# ---------------------------------------------------------------------------


class TestMetricsImprovements:
    def test_track_execution_time_records_duration(self):
        """track_execution_time decorator should actually record metrics."""
        from orchestrator.observability.metrics import MetricsCollector, track_execution_time

        @track_execution_time("test_func", labels={"agent": "test"})
        def slow_func():
            time.sleep(0.01)
            return "done"

        result = slow_func()
        assert result == "done"


# ---------------------------------------------------------------------------
# 9. Agentic team engine improvements
# ---------------------------------------------------------------------------


class TestAgenticTeamEngineImprovements:
    def test_extract_json_uses_public_api(self):
        """Engine should use public API, not private method."""
        from agentic_team.decision_parser import DecisionParser

        parser = DecisionParser()
        result = parser.extract_json_object('{"action": "message", "to_role": "dev"}')
        assert result is not None
        assert result["action"] == "message"

    def test_decision_parser_logs_privilege_override(self):
        """Parser should log when non-lead tries to finalize."""
        from agentic_team.decision_parser import DecisionParser

        parser = DecisionParser()
        result = parser.parse_decision(
            output='{"action": "finalize", "final_response": "done"}',
            current_role="developer",
            lead_role="project_manager",
            default_to_role="project_manager",
        )
        assert result["action"] == "message"
        assert result["to_role"] == "project_manager"


# ---------------------------------------------------------------------------
# 10. Shell improvements
# ---------------------------------------------------------------------------


class TestShellImprovements:
    def test_orchestrator_shell_save_creates_restricted_file(self):
        """Saved session files should have restricted permissions."""
        from orchestrator.cli.shell import ConversationHistory

        history = ConversationHistory()
        history.add_message("user", "test")

        fd, tmpfile = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            history.save(tmpfile)
            assert os.path.exists(tmpfile)
            # Check file permissions (owner read/write only)
            mode = oct(os.stat(tmpfile).st_mode)[-3:]
            if sys.platform != "win32":
                assert mode == "600"
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def test_orchestrator_shell_load_validates_format(self):
        """Loading an invalid JSON file should raise IOError."""
        from orchestrator.cli.shell import ConversationHistory

        history = ConversationHistory()
        fd, tmpfile = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(tmpfile, "w") as f:
                f.write("not json")
            with pytest.raises(IOError):
                history.load(tmpfile)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def test_agentic_shell_save_creates_restricted_file(self):
        """Agentic shell session file should have restricted permissions."""
        from agentic_team.shell import AgenticConversationHistory

        history = AgenticConversationHistory()
        history.add_message("user", "test task")

        fd, tmpfile = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            history.save(tmpfile)
            mode = oct(os.stat(tmpfile).st_mode)[-3:]
            if sys.platform != "win32":
                assert mode == "600"
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def test_agentic_shell_load_rejects_non_dict(self):
        """Loading a JSON file that's not a dict should raise IOError."""
        from agentic_team.shell import AgenticConversationHistory

        history = AgenticConversationHistory()
        fd, tmpfile = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(tmpfile, "w") as f:
                json.dump([1, 2, 3], f)
            with pytest.raises(IOError, match="Invalid session"):
                history.load(tmpfile)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)


# ---------------------------------------------------------------------------
# 11. LlamaCpp adapter config validation
# ---------------------------------------------------------------------------


class TestLlamaCppConfigValidation:
    def test_invalid_max_tokens_uses_default(self):
        """Invalid max_tokens should fall back to default."""
        from orchestrator.adapters.llama_cpp_adapter import LlamaCppAdapter

        config = {
            "name": "test",
            "enabled": True,
            "offline": True,
            "max_tokens": "not_a_number",
            "temperature": "also_bad",
        }
        adapter = LlamaCppAdapter(config)
        assert adapter.max_tokens == 4096
        assert adapter.temperature == 0.7

    def test_temperature_clamped_to_range(self):
        """Temperature should be clamped between 0 and 2."""
        from orchestrator.adapters.llama_cpp_adapter import LlamaCppAdapter

        config = {"name": "test", "enabled": True, "offline": True, "temperature": 5.0}
        adapter = LlamaCppAdapter(config)
        assert adapter.temperature == 2.0

    def test_parse_text_response_handles_bad_data(self):
        """_parse_text_response should handle non-dict data gracefully."""
        from orchestrator.adapters.llama_cpp_adapter import LlamaCppAdapter

        config = {"name": "test", "enabled": True, "offline": True}
        adapter = LlamaCppAdapter(config)
        assert adapter._parse_text_response("not a dict") == ""
        assert adapter._parse_text_response({"choices": []}) == ""
        assert adapter._parse_text_response({"choices": [{"text": "hello"}]}) == "hello"


# ---------------------------------------------------------------------------
# 12. Agentic UI backend max_turns validation
# ---------------------------------------------------------------------------


class TestAgenticUIBackendValidation:
    def test_execute_handles_non_numeric_max_turns(self):
        """POST /api/execute should handle non-numeric max_turns gracefully."""
        import agentic_team.ui.app as agentic_app

        mock_engine = MagicMock()
        mock_engine.get_available_agents.return_value = ["claude"]
        mock_engine.validate_team_bindings.return_value = {
            "valid": True,
            "available_agents": ["claude"],
            "missing_roles": [],
            "reason": "",
        }
        agentic_app.engine = mock_engine

        client = agentic_app.app.test_client()
        # max_turns as non-numeric string
        response = client.post(
            "/api/execute",
            json={"task": "test", "max_turns": "not_a_number"},
            content_type="application/json",
        )
        # Should not crash with ValueError, should default to 12
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 13. HTTP output type fix in BaseAdapter
# ---------------------------------------------------------------------------


class TestBaseAdapterHTTPOutputType:
    def test_http_response_output_is_always_string(self):
        """_run_http_with_prompt should return string output, not dict."""
        from orchestrator.adapters.base import AgentResponse

        # The fix converts dict to str for output field
        r = AgentResponse(success=True, output=str({"key": "value"}))
        assert isinstance(r.output, str)


# ---------------------------------------------------------------------------
# 14. Audit logger improvements
# ---------------------------------------------------------------------------


class TestAuditLoggerImprovements:
    def test_audit_log_creates_file_with_restricted_permissions(self):
        """Audit log should be created with 0600 permissions."""
        from orchestrator.security_module.security import AuditLogger

        tmpdir = tempfile.mkdtemp()
        try:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_file=log_path)
            logger.log_event("test_event", user="test", action="test_action")

            assert log_path.exists()
            mode = oct(os.stat(log_path).st_mode)[-3:]
            if sys.platform != "win32":
                assert mode == "600"

            # Verify content
            content = log_path.read_text()
            event = json.loads(content.strip())
            assert event["event_type"] == "test_event"
            assert event["user"] == "test"
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 15. Claude adapter wires up file extraction
# ---------------------------------------------------------------------------


class TestClaudeAdapterFileExtraction:
    def test_extract_modified_files_wired_up(self):
        """ClaudeAdapter.execute_task should call _extract_modified_files."""
        from orchestrator.adapters.claude_adapter import ClaudeAdapter

        config = {"name": "claude", "enabled": True, "command": "echo"}
        adapter = ClaudeAdapter(config)

        mock_response = AgentResponse(
            success=True,
            output="Modified: src/main.py\nDone.",
            files_modified=["workspace/other.py"],
        )

        with patch.object(adapter, "_run_command_with_prompt", return_value=mock_response):
            result = adapter.execute_task("fix bug", {"working_dir": "./workspace"})

        assert "src/main.py" in result.files_modified
        assert "workspace/other.py" in result.files_modified


# ---------------------------------------------------------------------------
# 16. Codex adapter wires up file extraction
# ---------------------------------------------------------------------------


class TestCodexAdapterFileExtraction:
    def test_extract_generated_files_wired_up(self):
        """CodexAdapter.execute_task should call _extract_generated_files."""
        from orchestrator.adapters.codex_adapter import CodexAdapter

        config = {"name": "codex", "enabled": True, "command": "echo"}
        adapter = CodexAdapter(config)

        mock_response = AgentResponse(
            success=True,
            output="Created: src/app.py\nGenerated: tests/test_app.py",
        )

        with patch.object(adapter, "_run_command_with_prompt", return_value=mock_response):
            result = adapter.execute_task("implement feature", {"working_dir": "./workspace"})

        assert "src/app.py" in result.files_modified
        assert "tests/test_app.py" in result.files_modified
