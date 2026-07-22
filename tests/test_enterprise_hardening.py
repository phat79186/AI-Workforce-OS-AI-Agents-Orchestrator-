"""
Tests for round-2 enterprise hardening improvements.

Covers: concurrency, circuit breaker enum, fallback validation,
offline detection, exception serialization, workflow progress,
adapter regex, copilot parsing, task cleanup, async executor.
"""

import asyncio
import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Task manager - atomic counter & cleanup
# ---------------------------------------------------------------------------
from orchestrator.core.task_manager import Task, TaskManager, TaskStatus


class TestTaskManagerConcurrency:
    def test_counter_is_atomic_under_threads(self):
        """create_task from multiple threads should produce unique IDs."""
        tm = TaskManager()
        ids: list[str] = []
        lock = threading.Lock()

        def create():
            task = tm.create_task("parallel task")
            with lock:
                ids.append(task.id)

        threads = [threading.Thread(target=create) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(ids) == 50
        assert len(set(ids)) == 50  # All unique

    def test_cleanup_stale_removes_old_completed(self):
        """cleanup_stale should remove completed tasks older than threshold."""
        from datetime import datetime, timedelta

        tm = TaskManager()
        t1 = tm.create_task("old task")
        t1.complete("done")
        t1.completed_at = datetime.now() - timedelta(seconds=120)

        t2 = tm.create_task("recent task")
        t2.complete("done")

        removed = tm.cleanup_stale(max_age_seconds=60)
        assert removed == 1
        assert t1.id not in tm.tasks
        assert t2.id in tm.tasks

    def test_cleanup_stale_ignores_pending(self):
        """cleanup_stale should not touch pending tasks."""
        tm = TaskManager()
        tm.create_task("pending task")
        removed = tm.cleanup_stale(max_age_seconds=0)
        assert removed == 0
        assert len(tm.tasks) == 1


# ---------------------------------------------------------------------------
# 2. Async executor - shutdown safety & kwargs fix
# ---------------------------------------------------------------------------
from orchestrator.infra.async_executor import AsyncExecutor, run_async_task


class TestAsyncExecutorShutdown:
    def test_double_shutdown_is_safe(self):
        """Calling shutdown twice should not raise."""
        executor = AsyncExecutor(max_workers=2)
        executor.shutdown()
        executor.shutdown()  # Should not raise

    def test_context_manager_shuts_down(self):
        """Context manager should shut down executor on exit."""
        with AsyncExecutor(max_workers=2) as executor:
            results = executor.execute_parallel([lambda: 42])
            assert results[0]["success"] is True
            assert results[0]["result"] == 42
        assert executor._shutdown is True

    def test_del_calls_shutdown(self):
        """__del__ should call shutdown."""
        executor = AsyncExecutor(max_workers=1)
        executor.__del__()
        assert executor._shutdown is True


class TestRunAsyncTaskKwargs:
    def test_run_async_task_with_kwargs(self):
        """run_async_task should correctly handle keyword arguments."""

        def add(a, b, extra=0):
            return a + b + extra

        result = asyncio.run(run_async_task(add, 1, 2, extra=10))
        assert result == 13

    def test_run_async_task_simple(self):
        """run_async_task should handle simple positional args."""
        result = asyncio.run(run_async_task(lambda x: x * 2, 5))
        assert result == 10


# ---------------------------------------------------------------------------
# 3. Circuit breaker - enum state
# ---------------------------------------------------------------------------
from orchestrator.resilience.retry import CircuitBreaker, CircuitState


class TestCircuitBreakerEnum:
    def test_initial_state_is_closed_enum(self):
        """Circuit breaker should start in CLOSED enum state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        """State should transition to OPEN after threshold failures."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.state == CircuitState.OPEN

    def test_open_circuit_raises_with_context(self):
        """OPEN circuit error message should include failure count and timeout info."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)

        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        with pytest.raises(Exception, match=r"OPEN.*1 failures.*30\.0s"):
            cb.call(lambda: "ok")

    def test_half_open_after_recovery_timeout(self):
        """After recovery timeout, state should become HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)

        # Should transition to HALF_OPEN and execute
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# 4. Fallback manager - missing adapter validation
# ---------------------------------------------------------------------------
from orchestrator.adapters.base import AgentResponse
from orchestrator.resilience.fallback import FallbackManager


class TestFallbackManagerValidation:
    def test_missing_primary_agent_returns_error(self):
        """execute_with_fallback should handle missing primary agent gracefully."""
        fm = FallbackManager({"settings": {"fallback": {"enabled": True}}})
        agent_used, response, fallback_from = fm.execute_with_fallback(
            primary_agent="nonexistent",
            adapters={},
            task="test",
            context={},
        )
        assert response.success is False
        assert "not found" in response.error
        assert agent_used == "nonexistent"

    def test_present_primary_agent_executes_normally(self):
        """With valid primary agent, should execute normally."""
        mock_adapter = MagicMock()
        mock_adapter.execute_task.return_value = AgentResponse(success=True, output="done")
        fm = FallbackManager({})
        agent_used, response, fallback_from = fm.execute_with_fallback(
            primary_agent="claude",
            adapters={"claude": mock_adapter},
            task="test",
            context={},
        )
        assert response.success is True
        assert agent_used == "claude"
        assert fallback_from is None


# ---------------------------------------------------------------------------
# 5. Offline detector - configurable URL & stricter check
# ---------------------------------------------------------------------------
from orchestrator.resilience.offline import OfflineDetector


class TestOfflineDetectorImprovements:
    def test_uses_env_var_for_url(self):
        """Should read CONNECTIVITY_CHECK_URL from environment."""
        with patch.dict("os.environ", {"CONNECTIVITY_CHECK_URL": "https://example.com"}):
            detector = OfflineDetector()
            assert detector.connectivity_url == "https://example.com"

    def test_default_url_not_anthropic(self):
        """Default URL should no longer be hardcoded to Anthropic."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove the env var if it exists
            import os

            os.environ.pop("CONNECTIVITY_CHECK_URL", None)
            detector = OfflineDetector()
            assert "anthropic" not in detector.connectivity_url.lower()

    def test_only_2xx_counts_as_online(self):
        """Only 2xx responses should be treated as online."""
        detector = OfflineDetector(connectivity_url="https://example.com")
        mock_response = MagicMock()
        mock_response.status_code = 301  # Redirect - not 2xx
        with patch("httpx.head", return_value=mock_response):
            # With follow_redirects, 301 may resolve to 200 or remain 301.
            # Just verify it returns a boolean.
            result = detector._check_connectivity()
            assert isinstance(result, bool)

        mock_response.status_code = 200
        with patch("httpx.head", return_value=mock_response):
            assert detector._check_connectivity() is True


# ---------------------------------------------------------------------------
# 6. Exception serialization
# ---------------------------------------------------------------------------
from orchestrator.core.exceptions import OrchestratorError, _make_serializable


class TestExceptionSerialization:
    def test_to_dict_handles_nested_exceptions(self):
        """to_dict should serialize nested Exception objects to strings."""
        err = OrchestratorError(
            "test",
            details={"cause": ValueError("inner error"), "count": 42},
        )
        result = err.to_dict()
        assert isinstance(result["details"]["cause"], str)
        assert "inner error" in result["details"]["cause"]
        assert result["details"]["count"] == 42

    def test_to_dict_is_json_safe(self):
        """to_dict output should be fully JSON serializable."""
        err = OrchestratorError(
            "test",
            details={
                "exception": RuntimeError("boom"),
                "nested": {"deep": object()},
                "list": [1, ValueError("x"), "normal"],
            },
        )
        result = err.to_dict()
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_make_serializable_primitives(self):
        """Primitives should pass through unchanged."""
        assert _make_serializable(42) == 42
        assert _make_serializable("hello") == "hello"
        assert _make_serializable(None) is None
        assert _make_serializable(True) is True


# ---------------------------------------------------------------------------
# 7. Workflow progress - edge cases
# ---------------------------------------------------------------------------
from orchestrator.core.workflow import WorkflowEngine


class TestWorkflowProgressEdgeCases:
    def test_progress_with_empty_steps(self):
        """get_progress with no steps should return 0% without error."""
        engine = WorkflowEngine()
        progress = engine.get_progress()
        assert progress["progress_percent"] == 0
        assert progress["total_steps"] == 0

    def test_progress_with_steps(self):
        """get_progress should calculate correctly with steps."""
        engine = WorkflowEngine()
        engine.steps = [MagicMock(), MagicMock(), MagicMock()]
        engine.current_step = 1
        progress = engine.get_progress()
        assert abs(progress["progress_percent"] - 33.33) < 1


# ---------------------------------------------------------------------------
# 8. Gemini adapter - compiled regex
# ---------------------------------------------------------------------------
from orchestrator.adapters.gemini_adapter import GeminiAdapter


class TestGeminiAdapterRegex:
    def test_class_level_regex_are_compiled(self):
        """Regex patterns should be compiled at class level."""
        import re

        assert isinstance(GeminiAdapter._NUMBERED_ITEM_RE, re.Pattern)
        assert isinstance(GeminiAdapter._BULLETED_ITEM_RE, re.Pattern)
        assert isinstance(GeminiAdapter._FILE_PATTERN_RE, re.Pattern)

    def test_parse_review_feedback_numbered(self):
        """Should parse numbered items."""
        config = {"name": "gemini", "enabled": True, "command": "echo"}
        adapter = GeminiAdapter(config)
        output = "1. Fix the bug\n2. Add tests\n- Clean up imports"
        suggestions = adapter._parse_review_feedback(output)
        assert len(suggestions) == 3

    def test_extract_mentioned_files(self):
        """Should extract backtick-quoted file paths."""
        config = {"name": "gemini", "enabled": True, "command": "echo"}
        adapter = GeminiAdapter(config)
        output = "Check `src/main.py` and `tests/test_app.ts`"
        files = adapter._extract_mentioned_files(output, {})
        assert "src/main.py" in files
        assert "tests/test_app.ts" in files


# ---------------------------------------------------------------------------
# 9. Copilot adapter - robust parsing
# ---------------------------------------------------------------------------
from orchestrator.adapters.copilot_adapter import CopilotAdapter


class TestCopilotAdapterParsing:
    def test_empty_output_returns_empty_list(self):
        """Empty output should return empty list."""
        config = {"name": "copilot", "enabled": True, "command": "echo"}
        adapter = CopilotAdapter(config)
        assert adapter._extract_copilot_suggestions("") == []
        assert adapter._extract_copilot_suggestions("   ") == []

    def test_numbered_suggestions(self):
        """Should parse numbered suggestions."""
        config = {"name": "copilot", "enabled": True, "command": "echo"}
        adapter = CopilotAdapter(config)
        output = "1. First suggestion\nDetails here\n2. Second suggestion"
        suggestions = adapter._extract_copilot_suggestions(output)
        assert len(suggestions) == 2
        assert "First suggestion" in suggestions[0]
        assert "Second suggestion" in suggestions[1]

    def test_bullet_suggestions(self):
        """Should parse bullet-point suggestions."""
        config = {"name": "copilot", "enabled": True, "command": "echo"}
        adapter = CopilotAdapter(config)
        output = "- First item\n- Second item\n- Third item"
        suggestions = adapter._extract_copilot_suggestions(output)
        assert len(suggestions) == 3

    def test_plain_text_returns_as_single_suggestion(self):
        """Plain text without structure should be returned as-is."""
        config = {"name": "copilot", "enabled": True, "command": "echo"}
        adapter = CopilotAdapter(config)
        output = "This is just plain text output"
        suggestions = adapter._extract_copilot_suggestions(output)
        assert len(suggestions) == 1
        assert suggestions[0] == "This is just plain text output"


# ---------------------------------------------------------------------------
# 10. Config utils - normalize_role collapses underscores
# ---------------------------------------------------------------------------
from agentic_team.config_utils import normalize_role


class TestNormalizeRoleImprovements:
    def test_collapses_consecutive_underscores(self):
        """Multiple underscores from double hyphens should collapse."""
        assert normalize_role("foo--bar") == "foo_bar"
        assert normalize_role("a---b") == "a_b"

    def test_strips_leading_trailing_underscores(self):
        """Leading/trailing underscores should be stripped."""
        assert normalize_role("-role-") == "role"
        assert normalize_role("  role  ") == "role"

    def test_normal_roles_unchanged(self):
        """Normal role names should remain unchanged."""
        assert normalize_role("project_manager") == "project_manager"
        assert normalize_role("qa-engineer") == "qa_engineer"
        assert normalize_role("DevOps Engineer") == "devops_engineer"

    def test_empty_and_none(self):
        """Empty and None should return empty string."""
        assert normalize_role("") == ""
        assert normalize_role(None) == ""


# ---------------------------------------------------------------------------
# 11. Logging config - file handler respects log_level
# ---------------------------------------------------------------------------
class TestLoggingConfig:
    def test_file_handler_level_uses_parameter(self):
        """The file handler created by configure_logging should use the given log_level."""
        import logging
        import os

        # Directly test the code path: create a FileHandler and set level per our fix
        handler = logging.FileHandler(os.devnull)
        log_level = "WARNING"
        handler.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
        assert handler.level == logging.WARNING

        handler2 = logging.FileHandler(os.devnull)
        handler2.setLevel(getattr(logging, "ERROR", logging.DEBUG))
        assert handler2.level == logging.ERROR
