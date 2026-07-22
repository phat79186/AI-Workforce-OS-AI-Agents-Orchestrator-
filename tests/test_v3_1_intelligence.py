"""Unit tests for v3.1 Workforce Intelligence & AI CTO Manager."""

import tempfile
import pytest

from workforce import (
    AIEmployee,
    AIWorkforceRegistry,
    CandidateRanker,
    PerformanceMetrics,
    SeniorityLevel,
    WorkforceBudget,
)
from v3_orchestrator import AICTOManager


def test_performance_feedback_loop():
    metrics = PerformanceMetrics()
    assert metrics.reliability_score == 1.0

    # Simulate 2 successful runs
    metrics.update(success=True, test_passed=True, review_passed=True, duration_sec=5.0)
    metrics.update(success=True, test_passed=True, review_passed=True, duration_sec=3.0)

    assert metrics.tasks_completed == 2
    assert metrics.success_rate == 1.0
    assert metrics.avg_time_sec == 4.0
    assert metrics.reliability_score == 1.0

    # Simulate 1 failed run
    metrics.update(success=False, test_passed=False, review_passed=False, duration_sec=10.0)
    assert metrics.tasks_completed == 3
    assert metrics.success_rate == 0.67
    assert metrics.reliability_score < 1.0


def test_candidate_ranker_seniority_matching():
    ranker = CandidateRanker()

    junior = AIEmployee(
        employee_id="1",
        name="JuniorCoder",
        role="Coder",
        department="swe",
        provider_name="ollama",
        seniority=SeniorityLevel.JUNIOR,
        skills=["Python"],
    )

    senior = AIEmployee(
        employee_id="2",
        name="SeniorArchitect",
        role="Architect",
        department="swe",
        provider_name="ollama",
        seniority=SeniorityLevel.SENIOR,
        skills=["Python", "Architecture"],
    )

    # Complex architecture task (Complexity = 4)
    ranked = ranker.rank_candidates([junior, senior], required_skills=["Python", "Architecture"], task_complexity=4)
    best_candidate, best_score = ranked[0]

    assert best_candidate.name == "SeniorArchitect"
    assert best_score > ranked[1][1]


def test_workforce_budget_limits():
    budget = WorkforceBudget(max_total_agents=2, max_concurrent_agents=1)
    assert budget.validate_recruitment(current_total_agents=1, current_concurrent_agents=0) is True
    assert budget.validate_recruitment(current_total_agents=2, current_concurrent_agents=0) is False
    assert budget.validate_recruitment(current_total_agents=1, current_concurrent_agents=1) is False


def test_ai_cto_manager_cross_department_dag():
    with tempfile.TemporaryDirectory() as tmpdir:
        cto = AICTOManager(vault_path=tmpdir)
        graph = cto.plan_project("Xây hệ thống nhận diện khuôn mặt có liveness detection")

        assert len(graph.nodes) == 7
        assert "TASK-01-RESEARCH" in graph.nodes
        assert "TASK-02-SECURITY" in graph.nodes
        assert "TASK-04-BACKEND" in graph.nodes

        team = cto.recruit_team(graph)
        assert len(team) >= 1
        assert "TASK-01-RESEARCH" in team
