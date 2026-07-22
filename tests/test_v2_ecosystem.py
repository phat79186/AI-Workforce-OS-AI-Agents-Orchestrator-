"""Comprehensive unit test suite for AI Software Engineering OS v2.0 components."""

import tempfile
from pathlib import Path

import pytest

from orchestrator.core.dependency_graph import DependencyGraph
from orchestrator.core.task_queue import TaskQueue
from orchestrator.events import Event, EventBus, EventStore, EventType
from orchestrator.security import ActionLevel, ApprovalManager, PermissionPolicy, SecuritySandbox
from orchestrator.context.obsidian_rag import ObsidianVaultRAG
from orchestrator.observability.metrics_analyzer import MetricsAnalyzer


def test_dependency_graph_dag():
    graph = DependencyGraph()
    t1 = graph.add_task("T1", "Research architecture", "Research Agent")
    t2 = graph.add_task("T2", "Implement backend", "Coding Agent", dependencies=["T1"])

    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].task_id == "T1"

    graph.mark_completed("T1")
    ready2 = graph.get_ready_tasks()
    assert len(ready2) == 1
    assert ready2[0].task_id == "T2"

    graph.mark_completed("T2")
    assert graph.is_all_completed() is True


def test_task_queue():
    tq = TaskQueue()
    graph = DependencyGraph()
    t1 = graph.add_task("T1", "Write unit test", "Testing Agent")

    tq.enqueue(t1)
    assert tq.size() == 1
    item = tq.dequeue(timeout=0.1)
    assert item.task_id == "T1"


def test_event_bus():
    bus = EventBus()
    store = EventStore()
    received = []

    def handler(evt: Event):
        received.append(evt)
        store.record(evt)

    bus.subscribe(EventType.TASK_CREATED, handler)

    evt = Event(event_type=EventType.TASK_CREATED, task_id="T100", agent_role="Coding Agent")
    bus.publish(evt)

    assert len(received) == 1
    assert store.get_events(task_id="T100")[0].event_type == EventType.TASK_CREATED


def test_security_sandbox():
    policy = PermissionPolicy()
    assert policy.classify("pytest tests/") == ActionLevel.ALLOWED
    assert policy.classify("rm -rf database/") == ActionLevel.BLOCKED
    assert policy.classify("git push --force") == ActionLevel.REQUIRES_APPROVAL

    # Auto-approval mock function
    appr_mgr = ApprovalManager(prompt_fn=lambda action: True)
    sandbox = SecuritySandbox(policy=policy, approval_mgr=appr_mgr)

    blocked_res = sandbox.validate_and_execute("rm -rf database/", lambda cmd: "deleted")
    assert blocked_res["status"] == "blocked"

    allowed_res = sandbox.validate_and_execute("pytest", lambda cmd: "passed")
    assert allowed_res["status"] == "success"
    assert allowed_res["result"] == "passed"


def test_obsidian_rag():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        (vault / "ADR-001.md").write_text("# Face Liveness ADR\nArchitecture for Liveness feature.", encoding="utf-8")
        (vault / "Glossary.md").write_text("# Glossary\nLiveness definition and specs.", encoding="utf-8")

        rag = ObsidianVaultRAG(str(vault))
        assert len(rag._documents) == 2

        results = rag.query("Liveness architecture")
        assert len(results) >= 1
        assert "Liveness" in results[0]["title"] or "Liveness" in results[0]["content"]


def test_metrics_analyzer():
    analyzer = MetricsAnalyzer()
    analyzer.record_outcome("Coding Agent", "ollama-qwen2.5-coder:7b", "implement", True)
    analyzer.record_outcome("Coding Agent", "ollama-qwen2.5-coder:7b", "implement", True)
    analyzer.record_outcome("Coding Agent", "openhands", "implement", False)

    rates = analyzer.calculate_success_rates()
    assert rates["Coding Agent::ollama-qwen2.5-coder:7b"] == 1.0
    assert rates["Coding Agent::openhands"] == 0.0
