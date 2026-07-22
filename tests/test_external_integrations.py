"""Unit tests for 8 External Tools & Skills Integrations in AI Workforce OS v4.2."""

import pytest
from orchestrator.integrations import (
    MattPocockSkillsEngine,
    CodeGraphTool,
    PonytailRunner,
    AnySearchSkill,
    UIUXProMaxSkill,
    ImpeccableDesignSkill,
    PublicAPIsCatalog,
    SAGAgentFramework,
    ExternalEcosystemHub,
)


def test_mattpocock_skills_integration():
    engine = MattPocockSkillsEngine()
    skill = engine.find_skill("typescript-pro")

    assert skill is not None
    assert skill.name == "typescript-pro"
    assert "typescript" in skill.tags


def test_codegraph_tool_integration():
    cg = CodeGraphTool()
    info = cg.explore_symbol("execute_corporate_initiative")

    assert info is not None
    assert info["line"] == 32
    assert "formulate_strategy" in info["callees"]


def test_ponytail_runner_integration():
    runner = PonytailRunner()
    runner.add_step("STEP-1", "code_review", "Reviewer")
    res = runner.execute_workflow()

    assert res["status"] == "SUCCESS"
    assert res["total_steps"] == 1


def test_anysearch_skill_integration():
    search = AnySearchSkill()
    res = search.execute_search("Face Liveness Security")

    assert res["status"] == "COMPLETED"
    assert "codebase" in res["sources_searched"]


def test_ui_ux_pro_max_integration():
    ui_skill = UIUXProMaxSkill()
    ds = ui_skill.generate_design_system("Dark Glassmorphism")

    assert ds["status"] == "READY"
    assert ds["palette"]["primary"] == "#6366f1"


def test_impeccable_design_integration():
    imp = ImpeccableDesignSkill()
    audit = imp.audit_ui_component("Navbar")

    assert audit["status"] == "APPROVED"
    assert audit["wcag_compliance"] == "AA Passed"


def test_public_apis_catalog_integration():
    cat = PublicAPIsCatalog()
    results = cat.search_apis("Security")

    assert len(results) >= 1
    assert "Face Recognition API" in results[0].api_name


def test_sag_framework_integration():
    sag = SAGAgentFramework()
    sag.register_agent("AGENT-1", "Architect", {"state": "active"})
    res = sag.synchronize_graph()

    assert res["status"] == "SYNCHRONIZED"
    assert res["node_count"] == 1


def test_external_ecosystem_hub():
    hub = ExternalEcosystemHub()
    status = hub.get_status()

    assert status["overall_status"] == "ALL_8_INTEGRATED"
    assert status["public_apis_count"] >= 2
