"""
Tests for BaseAdapter execution methods — the actual code paths that
invoke CLI tools and HTTP endpoints. These are the most critical paths
for production correctness.
"""

import subprocess
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from orchestrator.adapters.base import AgentCapability, AgentResponse, BaseAdapter


class ConcreteAdapter(BaseAdapter):
    """Concrete adapter for testing base class methods."""

    def get_capabilities(self):
        return [AgentCapability.IMPLEMENTATION]

    def execute_task(self, task, context):
        return self._run_command_with_prompt(task, context.get("working_dir"))


# ===================================================================
# _run_command_with_prompt — workspace path
# ===================================================================


class TestRunCommandWithPromptWorkspace:
    """Test CLI execution via workspace tracking."""

    def test_workspace_execution_success(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)
        adapter.cli_pattern = {"method": "arg", "supports_workspace": True}
        adapter.cli_communicator = MagicMock()
        adapter.cli_communicator.execute_in_workspace.return_value = (
            True,
            "output text",
            "",
            ["file1.py", "file2.py"],
        )

        resp = adapter._run_command_with_prompt("do stuff", working_dir="./ws", use_workspace=True)

        assert resp.success is True
        assert resp.output == "output text"
        assert resp.files_modified == ["file1.py", "file2.py"]
        assert resp.metadata["working_dir"] == "./ws"
        adapter.cli_communicator.execute_in_workspace.assert_called_once()

    def test_workspace_defaults_working_dir(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)
        adapter.cli_pattern = {"method": "arg", "supports_workspace": True}
        adapter.cli_communicator = MagicMock()
        adapter.cli_communicator.execute_in_workspace.return_value = (True, "ok", "", [])

        adapter._run_command_with_prompt("test", working_dir=None, use_workspace=True)

        call_kwargs = adapter.cli_communicator.execute_in_workspace.call_args
        assert (
            call_kwargs.kwargs.get("workspace_dir") == "./workspace"
            or call_kwargs[1].get("workspace_dir") == "./workspace"
        )

    def test_workspace_failure_returns_error(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)
        adapter.cli_pattern = {"method": "arg", "supports_workspace": True}
        adapter.cli_communicator = MagicMock()
        adapter.cli_communicator.execute_in_workspace.return_value = (
            False,
            "",
            "command not found",
            [],
        )

        resp = adapter._run_command_with_prompt("test", working_dir="./ws", use_workspace=True)

        assert resp.success is False
        assert resp.error == "command not found"


# ===================================================================
# _run_command_with_prompt — non-workspace path
# ===================================================================


class TestRunCommandWithPromptStandard:
    """Test CLI execution via execute_with_retry."""

    def test_standard_execution_success(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)
        adapter.cli_pattern = {"method": "arg", "supports_workspace": False}
        adapter.cli_communicator = MagicMock()
        adapter.cli_communicator.execute_with_retry.return_value = (True, "result", "")

        resp = adapter._run_command_with_prompt("test prompt", use_workspace=False)

        assert resp.success is True
        assert resp.output == "result"
        assert resp.error is None

    def test_standard_execution_failure(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)
        adapter.cli_pattern = {"method": "arg", "supports_workspace": False}
        adapter.cli_communicator = MagicMock()
        adapter.cli_communicator.execute_with_retry.return_value = (False, "", "error msg")

        resp = adapter._run_command_with_prompt("test", use_workspace=False)

        assert resp.success is False
        assert resp.error == "error msg"

    def test_exception_in_execution_returns_error_response(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)
        adapter.cli_pattern = {"method": "arg", "supports_workspace": False}
        adapter.cli_communicator = MagicMock()
        adapter.cli_communicator.execute_with_retry.side_effect = RuntimeError("crash")

        resp = adapter._run_command_with_prompt("test", use_workspace=False)

        assert resp.success is False
        assert "crash" in resp.error


# ===================================================================
# _run_http_with_prompt
# ===================================================================


class TestRunHTTPWithPrompt:
    """Test HTTP execution for local model endpoints."""

    def test_http_success_dict_response(self):
        config = {
            "name": "local",
            "command": "",
            "enabled": True,
            "offline": True,
            "endpoint": "http://localhost:8080",
        }
        adapter = ConcreteAdapter(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "hello world"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            resp = adapter._run_http_with_prompt({"prompt": "hello"})

        assert resp.success is True
        assert isinstance(resp.output, str)  # Should be string, not dict
        assert "hello world" in resp.output

    def test_http_status_error(self):
        config = {
            "name": "local",
            "command": "",
            "enabled": True,
            "offline": True,
            "endpoint": "http://localhost:8080",
        }
        adapter = ConcreteAdapter(config)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            resp = adapter._run_http_with_prompt({"prompt": "hello"})

        assert resp.success is False
        assert "HTTP error" in resp.error

    def test_http_connection_error(self):
        config = {
            "name": "local",
            "command": "",
            "enabled": True,
            "offline": True,
            "endpoint": "http://localhost:9999",
        }
        adapter = ConcreteAdapter(config)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            resp = adapter._run_http_with_prompt({"prompt": "hello"})

        assert resp.success is False
        assert "Connection error" in resp.error


# ===================================================================
# _run_command (legacy)
# ===================================================================


class TestRunCommandLegacy:
    """Test the legacy _run_command method."""

    def test_success(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("output", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            resp = adapter._run_command(["echo", "hello"])

        assert resp.success is True
        assert resp.output == "output"
        assert resp.metadata["returncode"] == 0

    def test_failure(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "error msg")
            mock_proc.returncode = 1
            mock_popen.return_value = mock_proc

            resp = adapter._run_command(["bad_cmd"])

        assert resp.success is False
        assert resp.error == "error msg"

    def test_timeout(self):
        config = {"name": "test", "command": "echo", "enabled": True, "timeout": 1}
        adapter = ConcreteAdapter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = subprocess.TimeoutExpired("cmd", 1)
            mock_proc.kill = MagicMock()
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc

            resp = adapter._run_command(["slow_cmd"])

        assert resp.success is False
        assert "timed out" in resp.error
        mock_proc.kill.assert_called_once()
        mock_proc.wait.assert_called_once()

    def test_exception(self):
        config = {"name": "test", "command": "echo", "enabled": True}
        adapter = ConcreteAdapter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError("not found")

            resp = adapter._run_command(["nonexistent"])

        assert resp.success is False
        assert "not found" in resp.error


# ===================================================================
# format_task_prompt
# ===================================================================


class TestFormatTaskPrompt:
    """Test prompt building with various context fields."""

    def test_basic_prompt(self):
        config = {"name": "test", "command": "echo", "enabled": True, "offline": True}
        adapter = ConcreteAdapter(config)
        result = adapter.format_task_prompt("do thing", {})
        assert result == "do thing"

    def test_with_all_context(self):
        config = {"name": "test", "command": "echo", "enabled": True, "offline": True}
        adapter = ConcreteAdapter(config)
        result = adapter.format_task_prompt(
            "task",
            {
                "previous_output": "prev out",
                "feedback": "fix the bug",
                "files": ["a.py", "b.py"],
            },
        )
        assert "prev out" in result
        assert "fix the bug" in result
        assert "a.py" in result
        assert "b.py" in result

    def test_with_partial_context(self):
        config = {"name": "test", "command": "echo", "enabled": True, "offline": True}
        adapter = ConcreteAdapter(config)
        result = adapter.format_task_prompt("task", {"feedback": "improve error handling"})
        assert "improve error handling" in result
        assert "Previous output" not in result


# ===================================================================
# _build_local_llm_prompt
# ===================================================================


class TestBuildLocalLLMPrompt:
    """Test prompt construction for local LLM models."""

    def _adapter(self):
        config = {"name": "test", "command": "", "enabled": True, "offline": True}
        return ConcreteAdapter(config)

    def test_implement_role(self):
        r = self._adapter()._build_local_llm_prompt("build auth", {"role": "implement"})
        assert "expert software engineer" in r.lower()
        assert "build auth" in r

    def test_review_role(self):
        r = self._adapter()._build_local_llm_prompt(
            "check code", {"role": "review", "implementation": "def foo(): pass"}
        )
        assert "code reviewer" in r.lower()
        assert "def foo(): pass" in r

    def test_refine_role_with_feedback(self):
        r = self._adapter()._build_local_llm_prompt(
            "improve", {"role": "refine", "feedback": "add types", "implementation": "x = 1"}
        )
        assert "add types" in r
        assert "x = 1" in r

    def test_test_role(self):
        r = self._adapter()._build_local_llm_prompt("test it", {"role": "test"})
        assert "test" in r.lower()

    def test_document_role(self):
        r = self._adapter()._build_local_llm_prompt("doc it", {"role": "document"})
        assert "documentation" in r.lower()

    def test_generic_role(self):
        r = self._adapter()._build_local_llm_prompt("just do it", {"role": "other"})
        assert "just do it" in r

    def test_previous_output_appended(self):
        r = self._adapter()._build_local_llm_prompt(
            "task", {"role": "implement", "previous_output": "prior result"}
        )
        assert "prior result" in r
