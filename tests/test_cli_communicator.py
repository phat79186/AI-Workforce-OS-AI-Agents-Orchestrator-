"""Tests for CLI communicator command building and command parsing."""

from unittest.mock import Mock, patch

from orchestrator.adapters.base import AgentResponse, BaseAdapter
from orchestrator.adapters.cli_communicator import CLICommunicator


class _DummyAdapter(BaseAdapter):
    def get_capabilities(self):
        return []

    def execute_task(self, task, context):
        return AgentResponse(success=True, output="")


def test_build_codex_command_with_extra_args():
    communicator = CLICommunicator("codex -m gpt-5")
    command = communicator._build_command_for_tool("implement feature")

    assert command == ["codex", "-m", "gpt-5", "exec", "implement feature"]


def test_build_codex_command_without_duplicate_exec():
    communicator = CLICommunicator("codex exec -m gpt-5")
    command = communicator._build_command_for_tool("review this")

    assert command == ["codex", "exec", "-m", "gpt-5", "review this"]


def test_base_adapter_is_available_uses_binary_when_command_has_args():
    config = {"name": "test", "command": "codex -m gpt-5", "enabled": True}
    adapter = _DummyAdapter(config)

    with patch("orchestrator.adapters.base.shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/codex"
        assert adapter.is_available() is True
        mock_which.assert_called_once_with("codex")


def test_retry_methods_codex_stay_arg_only():
    communicator = CLICommunicator("codex")
    assert communicator._resolve_retry_methods("arg") == ["arg"]
    assert communicator._resolve_retry_methods("stdin") == ["arg"]


def test_retry_methods_non_codex_keep_fallbacks():
    communicator = CLICommunicator("gemini")
    assert communicator._resolve_retry_methods("arg") == ["arg", "stdin", "heredoc"]


def test_build_gemini_command_uses_positional_prompt():
    communicator = CLICommunicator("gemini")
    command = communicator._build_command_for_tool("review this code")

    assert command == ["gemini", "review this code"]


def test_build_claude_command_uses_positional_prompt():
    communicator = CLICommunicator("claude")
    command = communicator._build_command_for_tool("refine this implementation")

    assert command == ["claude", "refine this implementation"]


def test_build_copilot_command_uses_prompt_flag_and_allow_all_tools():
    communicator = CLICommunicator("copilot")
    command = communicator._build_command_for_tool("Fix the bug in main.js")

    assert command == ["copilot", "-p", "Fix the bug in main.js", "--allow-all-tools"]


def test_build_copilot_command_keeps_existing_allow_all_tools():
    communicator = CLICommunicator("copilot --allow-all-tools")
    command = communicator._build_command_for_tool("Fix the bug in main.js")

    assert command == ["copilot", "--allow-all-tools", "-p", "Fix the bug in main.js"]
