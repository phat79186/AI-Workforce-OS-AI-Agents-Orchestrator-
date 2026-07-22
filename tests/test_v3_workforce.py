"""Unit tests for v3.0 4-Layer AI Workforce Ecosystem."""

import tempfile
from pathlib import Path

import pytest
from domains import (
    SoftwareEngineeringDomain,
    ResearchDomain,
    DevOpsDomain,
    KnowledgeManagementDomain,
)
from shared_knowledge import KnowledgeBridge
from workforce import AIEmployee, AIWorkforceRegistry
from v3_orchestrator import V3WorkforceManager


def test_layer2_domain_ecosystems():
    swe = SoftwareEngineeringDomain()
    assert swe.metadata.name == "software_engineering"
    assert "coder" in swe.get_roles()
    assert "feature" in swe.get_workflows()

    research = ResearchDomain()
    assert "researcher" in research.get_roles()

    devops = DevOpsDomain()
    assert "devops_engineer" in devops.get_roles()


def test_layer3_shared_knowledge_bridge():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "vault"
        bridge = KnowledgeBridge(vault_path=str(vault_path))

        # Research Agent publishes research on Face Liveness
        doc_file = bridge.publish_research(
            title="Face Liveness ADR",
            content="Use passive liveness detection with anti-spoofing models.",
            category="Security",
        )
        assert Path(doc_file).exists()

        # Coding Agent retrieves shared knowledge before implementing
        results = bridge.retrieve_context_for_agent("Face Liveness anti-spoofing")
        assert len(results) >= 1
        assert "Face Liveness" in results[0]["title"] or "liveness" in results[0]["content"].lower()


def test_layer4_ai_workforce_recruitment():
    registry = AIWorkforceRegistry()
    
    # Recruit for Python & Bugfix -> Should match JuniorCoder
    emp = registry.recruit("Python", "Bugfix")
    assert emp is not None
    assert emp.name == "JuniorCoder"
    assert emp.department == "software_engineering"

    # Recruit for Web Research -> Should match Researcher
    researcher = registry.recruit("Web Research", "RAG")
    assert researcher is not None
    assert researcher.name == "Researcher"


def test_v3_workforce_manager_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = V3WorkforceManager(vault_path=tmpdir)

        res = manager.execute_task(
            task_description="Implement Face Liveness feature and write tests",
            required_skills=["Python", "Testing"],
        )

        assert res["status"] == "completed"
        assert res["assigned_employee"] in ("JuniorCoder", "SeniorArchitect", "Researcher", "SecuritySpecialist")
        assert len(manager.event_store.get_events()) >= 2
