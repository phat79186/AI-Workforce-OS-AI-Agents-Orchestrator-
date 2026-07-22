"""
Targeted tests to cover critical untested code paths.

Focuses on: decision_parser extraction, workflow engine execute,
WorkflowStep task descriptions, BaseAdapter.is_available with shutil.which,
and the full WorkflowEngine.execute chain.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.adapters.base import AgentCapability, AgentResponse, BaseAdapter

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


class SimpleAdapter(BaseAdapter):
    """Minimal adapter for testing."""

    def __init__(self, config, response=None):
        self.config = config
        self.name = config.get("name", "simple")
        self.command = config.get("command", "echo")
        self.endpoint = ""
        self.enabled = config.get("enabled", True)
        self.timeout = 10
        self.cli_communicator = None
        self.cli_pattern = {"method": "arg", "supports_workspace": False}
        self.communication_method = "arg"
        self._response = response or AgentResponse(success=True, output="ok")
        import logging

        self.logger = logging.getLogger(f"adapter.{self.name}")

    def get_capabilities(self):
        return [AgentCapability.IMPLEMENTATION]

    def execute_task(self, task, context):
        return self._response


# ===================================================================
# 1. DecisionParser - all extraction paths
# ===================================================================

from agentic_team.decision_parser import DecisionParser


class TestDecisionParserExtraction:
    """Cover fenced-block, streaming scan, and KV-line extraction."""

    def setup_method(self):
        self.parser = DecisionParser()

    def test_direct_json(self):
        """Pure JSON string should be parsed directly."""
        r = self.parser.extract_json_object('{"action": "message"}')
        assert r == {"action": "message"}

    def test_fenced_block_extraction(self):
        """JSON in a markdown fenced block should be extracted."""
        text = 'Here is my response:\n```json\n{"action":"finalize","final_response":"done"}\n```\nEnd.'
        r = self.parser.extract_json_object(text)
        assert r is not None
        assert r["action"] == "finalize"

    def test_fenced_block_without_json_tag(self):
        """Fenced block without `json` tag should still work."""
        text = 'Result:\n```\n{"to_role": "dev"}\n```'
        r = self.parser.extract_json_object(text)
        assert r is not None
        assert r["to_role"] == "dev"

    def test_streaming_scan_embedded_json(self):
        """JSON embedded in prose should be found by streaming scan."""
        text = 'I think the answer is {"action":"message","to_role":"qa","message":"test"} and that is it.'
        r = self.parser.extract_json_object(text)
        assert r is not None
        assert r["action"] == "message"
        assert r["to_role"] == "qa"

    def test_no_json_returns_none(self):
        """Plain text with no JSON should return None."""
        assert self.parser.extract_json_object("just some text") is None

    def test_empty_returns_none(self):
        assert self.parser.extract_json_object("") is None
        assert self.parser.extract_json_object(None) is None

    def test_json_array_not_returned(self):
        """JSON arrays should not be returned (we want objects)."""
        assert self.parser.extract_json_object("[1, 2, 3]") is None

    def test_kv_line_extraction(self):
        """Key-value lines should be parsed as fallback."""
        text = "action: message\nto_role: software_developer\nfinal_response: all done"
        r = self.parser._extract_from_kv_lines(text)
        assert r["action"] == "message"
        assert r["to_role"] == "software_developer"
        assert r["final_response"] == "all done"

    def test_kv_line_empty(self):
        assert self.parser._extract_from_kv_lines("") == {}
        assert self.parser._extract_from_kv_lines(None) == {}


class TestDecisionParserParsing:
    """Cover parse_decision edge cases."""

    def setup_method(self):
        self.parser = DecisionParser()

    def test_invalid_action_defaults_to_message(self):
        result = self.parser.parse_decision(
            output='{"action":"sing","to_role":"dev","message":"hi"}',
            current_role="pm",
            lead_role="pm",
            default_to_role="pm",
        )
        assert result["action"] == "message"

    def test_missing_to_role_gets_default(self):
        result = self.parser.parse_decision(
            output='{"action":"message","message":"hi"}',
            current_role="pm",
            lead_role="pm",
            default_to_role="qa",
        )
        assert result["to_role"] == "qa"

    def test_message_field_falls_back_to_raw_output(self):
        """If no message key in JSON, raw output becomes the message."""
        result = self.parser.parse_decision(
            output='{"action":"message","to_role":"dev"}',
            current_role="pm",
            lead_role="pm",
            default_to_role="pm",
        )
        # Message should be the raw output since no 'message' key
        assert result["message"]  # Non-empty

    def test_finalize_extracts_final_response(self):
        result = self.parser.parse_decision(
            output='{"action":"finalize","final_response":"All done","message":"bye"}',
            current_role="pm",
            lead_role="pm",
            default_to_role="pm",
        )
        assert result["action"] == "finalize"
        assert result["final_response"] == "All done"

    def test_kv_fallback_when_no_json(self):
        """Plain text with KV lines should be parsed."""
        result = self.parser.parse_decision(
            output="action: message\nto_role: developer\nmessage: please implement",
            current_role="pm",
            lead_role="pm",
            default_to_role="pm",
        )
        assert result["action"] == "message"


# ===================================================================
# 2. WorkflowStep - all task type descriptions
# ===================================================================

from orchestrator.core.workflow import WorkflowEngine, WorkflowStep


class TestWorkflowStepDescriptions:
    """Cover all task_type branches in build_task_description."""

    def _make_step(self, task_type):
        adapter = SimpleAdapter({"name": "test"})
        return WorkflowStep(agent_name="test", task_type=task_type, adapter=adapter, config={})

    def test_implement(self):
        s = self._make_step("implement")
        assert "Implement" in s.build_task_description({"task": "foo"})

    def test_review(self):
        s = self._make_step("review")
        assert "Review" in s.build_task_description({"task": "foo"})

    def test_refine(self):
        s = self._make_step("refine")
        assert "Refine" in s.build_task_description({"task": "foo"})

    def test_test(self):
        s = self._make_step("test")
        assert "tests" in s.build_task_description({"task": "foo"}).lower()

    def test_document(self):
        s = self._make_step("document")
        assert "Document" in s.build_task_description({"task": "foo"})

    def test_unknown_returns_base_task(self):
        s = self._make_step("custom_thing")
        assert s.build_task_description({"task": "my task"}) == "my task"

    def test_build_step_context(self):
        s = self._make_step("review")
        ctx = s.build_step_context({"task": "foo", "extra": "bar"})
        assert ctx["role"] == "review"
        assert ctx["agent"] == "test"
        assert ctx["extra"] == "bar"


class TestWorkflowEngineExecute:
    """Cover WorkflowEngine.execute() including error path."""

    def test_execute_successful_chain(self):
        engine = WorkflowEngine()
        a1 = SimpleAdapter({"name": "a1"}, AgentResponse(success=True, output="step1 out"))
        a2 = SimpleAdapter({"name": "a2"}, AgentResponse(success=True, output="step2 out"))
        steps = [
            WorkflowStep("a1", "implement", a1, {}),
            WorkflowStep("a2", "review", a2, {}),
        ]
        engine.set_workflow(steps)
        results = engine.execute({"task": "test"})

        assert len(results) == 2
        assert results[0].success is True
        assert results[0].output == "step1 out"
        assert results[1].success is True

    def test_execute_step_failure_continues(self):
        """A failing step should produce error response but not stop execution."""
        engine = WorkflowEngine()

        class FailAdapter(SimpleAdapter):
            def execute_task(self, task, context):
                raise RuntimeError("boom")

        a1 = FailAdapter({"name": "a1"})
        a2 = SimpleAdapter({"name": "a2"}, AgentResponse(success=True, output="ok"))
        steps = [
            WorkflowStep("a1", "implement", a1, {}),
            WorkflowStep("a2", "review", a2, {}),
        ]
        engine.set_workflow(steps)
        results = engine.execute({"task": "test"})

        assert len(results) == 2
        assert results[0].success is False
        assert "boom" in results[0].error
        assert results[1].success is True

    def test_execute_empty_workflow(self):
        engine = WorkflowEngine()
        engine.set_workflow([])
        results = engine.execute({"task": "test"})
        assert results == []

    def test_context_propagation_between_steps(self):
        """Output of step N should be available as previous_output in step N+1."""
        engine = WorkflowEngine()
        captured_contexts = []

        class CapturingAdapter(SimpleAdapter):
            def execute_task(self, task, context):
                captured_contexts.append(dict(context))
                return AgentResponse(success=True, output=f"output_{len(captured_contexts)}")

        a1 = CapturingAdapter({"name": "a1"})
        a2 = CapturingAdapter({"name": "a2"})
        steps = [
            WorkflowStep("a1", "implement", a1, {}),
            WorkflowStep("a2", "review", a2, {}),
        ]
        engine.set_workflow(steps)
        engine.execute({"task": "test"})

        assert len(captured_contexts) == 2
        # Second step should see first step's output
        assert captured_contexts[1].get("previous_output") == "output_1"


# ===================================================================
# 3. BaseAdapter.is_available - shutil.which
# ===================================================================


class TestBaseAdapterIsAvailable:
    """Verify is_available uses shutil.which, not subprocess."""

    def test_available_when_command_found(self):
        adapter = SimpleAdapter({"name": "test", "command": "echo", "enabled": True})
        with patch("orchestrator.adapters.base.shutil.which", return_value="/usr/bin/echo") as mock:
            assert adapter.is_available() is True
            mock.assert_called_once_with("echo")

    def test_unavailable_when_command_not_found(self):
        adapter = SimpleAdapter({"name": "test", "command": "nonexistent_xyz", "enabled": True})
        with patch("orchestrator.adapters.base.shutil.which", return_value=None) as mock:
            assert adapter.is_available() is False

    def test_disabled_adapter_not_available(self):
        adapter = SimpleAdapter({"name": "test", "command": "echo", "enabled": False})
        assert adapter.is_available() is False

    def test_command_with_args_extracts_binary(self):
        """'codex --profile custom' should check just 'codex'."""
        adapter = SimpleAdapter(
            {"name": "test", "command": "codex --profile custom", "enabled": True}
        )
        with patch(
            "orchestrator.adapters.base.shutil.which", return_value="/usr/bin/codex"
        ) as mock:
            assert adapter.is_available() is True
            mock.assert_called_once_with("codex")


# ===================================================================
# 4. WorkflowStep.execute and execute_with_adapter
# ===================================================================


class TestWorkflowStepExecute:
    def test_execute_delegates_to_adapter(self):
        resp = AgentResponse(success=True, output="result")
        adapter = SimpleAdapter({"name": "a"}, resp)
        step = WorkflowStep("a", "implement", adapter, {})
        result = step.execute({"task": "build it"})
        assert result.success is True
        assert result.output == "result"

    def test_execute_with_adapter_uses_provided_adapter(self):
        original = SimpleAdapter({"name": "orig"}, AgentResponse(success=True, output="orig"))
        override = SimpleAdapter({"name": "over"}, AgentResponse(success=True, output="override"))
        step = WorkflowStep("orig", "implement", original, {})
        result = step.execute_with_adapter(override, {"task": "test"})
        assert result.output == "override"
