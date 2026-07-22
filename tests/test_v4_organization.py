"""Unit tests for v4.0 Autonomous AI Organization."""

import tempfile
import pytest
from v4_organization import (
    AICEOManager,
    AICTO,
    AutonomousAIOrganization,
    EngineeringManager,
    OperationsManager,
    ResearchManager,
)
from workforce import AIWorkforceRegistry


def test_ai_ceo_strategy_formulation():
    ceo = AICEOManager()
    goal = ceo.formulate_strategy("Building enterprise AI platform")

    assert "GOAL-V4" in goal.goal_id
    assert len(goal.key_objectives) >= 2
    assert len(goal.success_metrics) >= 2


def test_ai_cto_technical_roadmap():
    ceo = AICEOManager()
    cto = AICTO()

    goal = ceo.formulate_strategy("Building face liveness recognition system")
    roadmap = cto.build_technical_roadmap(goal)

    assert len(roadmap.nodes) == 6
    assert "RESEARCH-01" in roadmap.nodes
    assert "ENG-ARCH-02" in roadmap.nodes
    assert "OPS-SEC-05" in roadmap.nodes


def test_department_managers_execution():
    workforce = AIWorkforceRegistry()
    eng = EngineeringManager(workforce)
    res = ResearchManager(workforce)
    ops = OperationsManager(workforce)

    res_out = res.execute_subtask("TASK-01", "Research AI security", "researcher")
    assert res_out.status == "COMPLETED"
    assert res_out.department_name == "research"

    eng_out = eng.execute_subtask("TASK-02", "Code backend logic", "coder")
    assert eng_out.status == "COMPLETED"
    assert eng_out.department_name == "engineering"

    ops_out = ops.execute_subtask("TASK-03", "Audit security", "security_auditor")
    assert ops_out.status == "COMPLETED"
    assert ops_out.department_name == "operations"


def test_autonomous_ai_organization_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        org = AutonomousAIOrganization(vault_path=tmpdir)

        res = org.execute_corporate_initiative("Building Face Liveness Detection Microservice")

        assert res["executive_report"]["status"] == "SUCCESS"
        assert res["total_subtasks"] == 6
        assert len(res["subtask_results"]) == 6
