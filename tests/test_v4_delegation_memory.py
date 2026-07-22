"""Unit tests for v4.1 AI-to-AI Delegation & Cross-Project Organizational Memory Learning."""

import tempfile
import pytest

from v4_organization import (
    AIToAIDelegator,
    AutonomousAIOrganization,
    OrganizationalLearningRecord,
    OrganizationalMemory,
)
from workforce import AIWorkforceRegistry


def test_ai_to_ai_delegation_tree():
    workforce = AIWorkforceRegistry()
    delegator = AIToAIDelegator(workforce)

    nodes = delegator.execute_delegation_tree("Face Liveness Recognition Platform")
    assert len(nodes) == 5

    titles = [n.subordinate_title for n in nodes]
    assert "Research Director" in titles
    assert "Security Director" in titles
    assert "Engineering Manager" in titles
    assert "QA Lead" in titles
    assert "DevOps Manager" in titles


def test_cross_project_organizational_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem = OrganizationalMemory(vault_path=tmpdir)

        # Save learnings from Project 1
        rec = OrganizationalLearningRecord(
            project_name="Face Liveness v1",
            lessons_learned=["Use passive liveness models to avoid active prompt delays"],
            architecture_decisions=["ADR-01: Microservices layout"],
            security_findings=["SEC-01: Anti-spoofing image frame check"],
            failed_approaches=["Client-side assertion without backend verification"],
            successful_patterns=["Pytest assertion suite"],
        )
        doc_path = mem.save_project_learnings(rec)
        assert doc_path is not None

        # Project 2 queries past organizational learnings
        learnings = mem.get_lessons_learned("Face Liveness anti-spoofing")
        assert len(learnings) >= 1
        assert "Learnings" in learnings[0]["title"] or "liveness" in learnings[0]["content"].lower()


def test_autonomous_organization_with_delegation_and_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        org = AutonomousAIOrganization(vault_path=tmpdir)

        # Run Project 1
        res1 = org.execute_corporate_initiative("Face Recognition microservice")
        assert res1["executive_report"]["status"] == "SUCCESS"
        assert len(res1["delegation_tree"]) == 5

        # Run Project 2 (consults Project 1 learnings)
        res2 = org.execute_corporate_initiative("Face Liveness microservice v2")
        assert res2["executive_report"]["status"] == "SUCCESS"
        assert res2["previous_learnings_consulted"] >= 1
