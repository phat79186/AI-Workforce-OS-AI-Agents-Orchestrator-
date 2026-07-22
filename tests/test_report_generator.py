"""Tests for the report generator module."""

import json
import tempfile
from pathlib import Path

import pytest

from orchestrator.observability.report_generator import ReportGenerator


@pytest.fixture
def reports_dir(tmp_path):
    return tmp_path / "reports"


@pytest.fixture
def generator(reports_dir):
    return ReportGenerator(reports_dir=str(reports_dir))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execution_result(success=True, workflow="default"):
    return {
        "task": "Build REST API",
        "workflow": workflow,
        "success": success,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": "code here",
                        "error": None,
                        "files_modified": ["api.py"],
                        "suggestions": ["add tests"],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": "looks good",
                        "error": None,
                        "files_modified": [],
                        "suggestions": [],
                    },
                ],
                "final_output": "looks good",
            }
        ],
        "final_output": "looks good",
    }


# ---------------------------------------------------------------------------
# Execution report
# ---------------------------------------------------------------------------


class TestExecutionReport:
    def test_creates_json_file(self, generator, reports_dir):
        result = _make_execution_result()
        path = generator.generate_execution_report(
            task="Build REST API",
            workflow="default",
            results=result,
            duration_seconds=12.5,
            available_agents=["codex", "gemini", "claude"],
        )

        assert path.exists()
        assert path.suffix == ".json"
        data = json.loads(path.read_text())
        assert data["report_type"] == "execution_summary"
        assert data["task"] == "Build REST API"
        assert data["workflow"] == "default"
        assert data["success"] is True
        assert data["duration_seconds"] == 12.5
        assert data["iterations"] == 1
        assert data["total_suggestions"] == 1
        assert len(data["steps"]) == 2

    def test_captures_fallbacks(self, generator):
        result = _make_execution_result()
        result["iterations"][0]["steps"][0]["fallback_from"] = "claude"
        path = generator.generate_execution_report(
            task="t",
            workflow="w",
            results=result,
            duration_seconds=1.0,
            available_agents=[],
        )
        data = json.loads(path.read_text())
        assert data["fallback_count"] == 1
        assert data["steps"][0]["fallback_from"] == "claude"

    def test_failed_execution(self, generator):
        result = _make_execution_result(success=False)
        result["iterations"][0]["steps"][1]["success"] = False
        result["iterations"][0]["steps"][1]["error"] = "timeout"
        path = generator.generate_execution_report(
            task="t",
            workflow="w",
            results=result,
            duration_seconds=30.0,
            available_agents=[],
        )
        data = json.loads(path.read_text())
        assert data["success"] is False


# ---------------------------------------------------------------------------
# Health report
# ---------------------------------------------------------------------------


class TestHealthReport:
    def test_generates_from_provided_results(self, generator, reports_dir):
        health = {
            "status": "healthy",
            "checks": [{"name": "python_version", "status": "healthy", "message": "3.11.5"}],
        }
        path = generator.generate_health_report(health_results=health)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["report_type"] == "system_health"
        assert data["overall_status"] == "healthy"
        assert data["system"]["python_version"]
        assert data["system"]["disk_free_gb"] > 0

    def test_runs_live_health_check(self, generator):
        path = generator.generate_health_report()
        data = json.loads(path.read_text())
        assert data["report_type"] == "system_health"
        assert data["overall_status"] in ("healthy", "degraded", "unhealthy")


# ---------------------------------------------------------------------------
# Config audit
# ---------------------------------------------------------------------------


class TestConfigAudit:
    def test_audits_config(self, generator, reports_dir):
        config = {
            "agents": {
                "codex": {
                    "type": "cli",
                    "enabled": True,
                    "command": "codex",
                    "role": "implementation",
                    "timeout": 3600,
                },
                "local": {
                    "type": "ollama",
                    "enabled": False,
                    "endpoint": "http://localhost:11434",
                    "offline": True,
                },
            },
            "workflows": {
                "default": [
                    {"agent": "codex", "task": "implement"},
                ],
            },
            "settings": {
                "max_iterations": 3,
                "output_dir": "./output",
                "reports_dir": "./reports",
                "offline": {"enabled": False},
                "fallback": {"enabled": True},
            },
        }
        path = generator.generate_config_audit(config)
        data = json.loads(path.read_text())
        assert data["report_type"] == "config_audit"
        assert data["enabled_agent_count"] == 1
        assert data["workflow_count"] == 1
        assert data["agents"]["codex"]["enabled"] is True
        assert data["agents"]["local"]["offline"] is True
        assert data["workflows"]["default"]["step_count"] == 1


# ---------------------------------------------------------------------------
# Agent performance report
# ---------------------------------------------------------------------------


class TestAgentPerformance:
    def test_aggregates_stats(self, generator):
        history = [
            _make_execution_result(),
            _make_execution_result(success=False),
        ]
        path = generator.generate_agent_performance_report(history)
        data = json.loads(path.read_text())
        assert data["report_type"] == "agent_performance"
        assert data["executions_analysed"] == 2
        assert "codex" in data["agents"]
        assert data["agents"]["codex"]["total_calls"] == 2
        assert data["agents"]["codex"]["success_rate"] == 1.0

    def test_empty_history(self, generator):
        path = generator.generate_agent_performance_report([])
        data = json.loads(path.read_text())
        assert data["agents"] == {}


# ---------------------------------------------------------------------------
# Workflow analytics
# ---------------------------------------------------------------------------


class TestWorkflowAnalytics:
    def test_aggregates_workflows(self, generator):
        history = [
            _make_execution_result(workflow="default"),
            _make_execution_result(workflow="default"),
            _make_execution_result(workflow="quick", success=False),
        ]
        path = generator.generate_workflow_analytics(history)
        data = json.loads(path.read_text())
        assert data["report_type"] == "workflow_analytics"
        assert data["workflows"]["default"]["total_runs"] == 2
        assert data["workflows"]["default"]["success_rate"] == 1.0
        assert data["workflows"]["quick"]["total_runs"] == 1


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------


class TestIndex:
    def test_index_accumulates_entries(self, generator, reports_dir):
        generator.generate_health_report(health_results={"status": "healthy", "checks": []})
        generator.generate_config_audit({"agents": {}, "workflows": {}, "settings": {}})

        index_path = reports_dir / "INDEX.json"
        assert index_path.exists()
        entries = json.loads(index_path.read_text())
        assert len(entries) == 2
        types = {e["type"] for e in entries}
        assert types == {"system_health", "config_audit"}

    def test_index_survives_corruption(self, generator, reports_dir):
        index_path = reports_dir / "INDEX.json"
        index_path.write_text("not valid json")
        generator.generate_health_report(health_results={"status": "ok", "checks": []})
        entries = json.loads(index_path.read_text())
        assert len(entries) == 1
