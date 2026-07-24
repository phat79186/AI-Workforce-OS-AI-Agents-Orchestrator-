"""Unit tests for 8 External Tools & Skills Integrations in AI Workforce OS v4.2."""

import pytest
from orchestrator.integrations import (
    MattPocockSkillsEngine,
    CodeGraphTool,
    PonytailRunner,
    AnySearchSkill,
    AgentReachEngine,
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


def test_agent_reach_engine():
    engine = AgentReachEngine()
    reach = engine.search_reach("Face Liveness Security", max_depth=2)

    assert reach["source_repo"] == "Panniantong/Agent-Reach"
    assert reach["reach_radius_score"] >= 0.7
    assert len(reach["citations"]) >= 3
    assert "GitHub API" in reach["engines_searched"]


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
    assert res["agent_reach_enabled"] is True
    assert res["agent_reach_source"] == "Panniantong/Agent-Reach"
    assert res["reach_metadata"] is not None


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


def test_taste_skill_integration():
    from orchestrator.integrations import TasteSkill
    taste = TasteSkill()
    curation = taste.curate_design_taste("ExecutiveDashboardHeader")

    assert curation["status"] == "CURATED_WITH_TASTE"
    assert curation["visual_taste_score"] >= 0.95
    assert "Inter, Outfit, sans-serif" in curation["typography_hierarchy"]["font_family"]
    assert len(curation["taste_guidelines"]) >= 3


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

    assert status["overall_status"] in ("ALL_INTEGRATED", "ALL_8_INTEGRATED")
    assert status["public_apis_count"] >= 2
    assert status.get("openclaw_status") == "READY"
    assert status.get("taste_skill_status") == "READY"
