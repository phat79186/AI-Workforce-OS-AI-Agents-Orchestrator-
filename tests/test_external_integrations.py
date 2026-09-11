"""Unit tests for the External Tools & Skills Integrations in AI Workforce OS v4.2."""

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
    PublicAPIsFetchError,
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
    """CodeGraphTool now does REAL ast-based parsing — index this project and check a real symbol."""
    cg = CodeGraphTool()
    summary = cg.index_directory(".")

    assert summary["symbols_indexed"] > 0
    assert summary["files_indexed"] > 0

    info = cg.explore_symbol("recruit")
    assert info is not None
    assert info["file"].replace("\\", "/") == "workforce/registry.py"


def test_ponytail_runner_integration():
    runner = PonytailRunner()
    runner.add_step("STEP-1", "code_review", "Reviewer")
    runner.add_step("STEP-2", "security_audit", "SecuritySpecialist", dependencies=["STEP-1"])
    res = runner.execute_workflow(parallel_dispatch=True)

    assert res["status"] == "SUCCESS"
    assert res["total_steps"] == 2
    assert res["execution_order"] == ["STEP-1", "STEP-2"]
    assert res["source_repo"] == "DietrichGebert/ponytail"


def test_anysearch_skill_integration():
    search = AnySearchSkill()
    res = search.execute_search("Face Liveness Security")

    assert res["status"] == "COMPLETED"
    assert "codebase" in res["sources_searched"]
    assert res["agent_reach_enabled"] is True
    assert res["agent_reach_source"] == "Panniantong/Agent-Reach"
    assert res["reach_metadata"] is not None


def test_ui_ux_pro_max_integration():
    """UIUXProMaxSkill now genuinely varies by theme and verifies contrast with real WCAG math."""
    ui_skill = UIUXProMaxSkill()
    ds = ui_skill.generate_design_system("Dark Glassmorphism")

    assert ds["status"] == "READY"
    assert ds["palette"]["primary"] == "#6366f1"
    assert ds["contrast_verified"]["wcag_aa_pass"] is True

    brutalism = ui_skill.generate_design_system("Neo Brutalism")
    assert brutalism["palette"]["primary"] != ds["palette"]["primary"]


def test_impeccable_design_integration():
    """ImpeccableDesignSkill now computes a REAL WCAG contrast ratio from given colors."""
    imp = ImpeccableDesignSkill()

    good = imp.audit_ui_component("Navbar", foreground_color="#000000", background_color="#ffffff")
    assert good["status"] == "APPROVED"
    assert good["wcag_compliance"] in ("AA", "AAA")
    assert good["contrast_ratio"] == "21.0:1"

    bad = imp.audit_ui_component("Navbar", foreground_color="#999999", background_color="#aaaaaa")
    assert bad["status"] == "REJECTED"
    assert bad["wcag_compliance"] == "FAIL"

    unknown = imp.audit_ui_component("Navbar")
    assert unknown["status"] == "NEEDS_INPUT"


def test_taste_skill_integration():
    """TasteSkill no longer fabricates a numeric taste score; it reports real contrast when given colors."""
    from orchestrator.integrations import TasteSkill
    taste = TasteSkill()

    curation = taste.curate_design_taste("ExecutiveDashboardHeader")
    assert curation["status"] == "GUIDELINES_PROVIDED"
    assert "visual_taste_score" not in curation
    assert "Inter, Outfit, sans-serif" in curation["typography_hierarchy"]["font_family"]
    assert len(curation["taste_guidelines"]) >= 3

    with_colors = taste.curate_design_taste(
        "ExecutiveDashboardHeader",
        context={"foreground_color": "#000000", "background_color": "#ffffff"},
    )
    assert with_colors["status"] == "GUIDELINES_PROVIDED_WITH_CONTRAST_CHECK"
    assert with_colors["measured_contrast"]["ratio"] == "21.0:1"
    assert with_colors["measured_contrast"]["wcag_aa_pass"] is True


def test_public_apis_catalog_integration():
    """PublicAPIsCatalog now fetches the REAL public-apis/public-apis README (network required)."""
    cat = PublicAPIsCatalog()
    try:
        n = cat.load()
    except PublicAPIsFetchError as e:
        pytest.skip(f"No network access to raw.githubusercontent.com: {e}")

    assert n > 500  # the real catalog has ~1,700 entries as of writing
    results = cat.search_apis("cat")
    assert len(results) >= 1
    assert all("cat" in r.name.lower() or "cat" in r.description.lower() for r in results)


def test_sag_framework_integration():
    sag = SAGAgentFramework()
    sag.register_agent("AGENT-1", "Architect", {"state": "active"})
    res = sag.synchronize_graph()

    assert res["status"] == "SYNCHRONIZED"
    assert res["node_count"] == 1


def test_chatdev_adapter_integration():
    from orchestrator.integrations import ChatDevAdapter
    chatdev = ChatDevAdapter()
    software = chatdev.run_virtual_software_company("MathUtils", "Build a Python math utility")

    assert software["status"] == "COMPLETED_SOFTWARE_DEVELOPMENT"
    assert software["source_repo"] == "OpenBMB/ChatDev"
    assert len(software["completed_phases"]) == 4
    assert "main.py" in software["generated_files"]


def test_rtk_token_compressor_integration():
    from orchestrator.integrations import RTKTokenCompressor
    rtk = RTKTokenCompressor()
    messages = [
        {"role": "system", "content": "You are an AI CTO. Formulate technical roadmap with DAG steps."},
        {"role": "agent", "content": "Executing task...\nExecuting task...\nTraceback: Exception in thread main."},
    ]
    res = rtk.compress_agent_dialog(messages)

    assert res["status"] == "DIALOG_COMPRESSED"
    assert res["source_repo"] == "rtk-ai/rtk"
    assert res["saved_total_tokens"] >= 0
    assert len(res["compressed_dialog"]) == 2


def test_karpathy_skills_and_ponytail_combined_integration():
    from orchestrator.integrations import KarpathySkillsEngine, PonytailRunner
    karpathy = KarpathySkillsEngine()
    skills = karpathy.list_skills()
    assert len(skills) >= 5

    skill_res = karpathy.execute_skill_pattern("nanogpt-transformer")
    assert skill_res["status"] == "PATTERN_EXECUTED"
    assert "transformer" in skill_res["tags"]

    # Combine Karpathy skill action inside Ponytail runner step
    runner = PonytailRunner()
    runner.add_step("NANO-GPT-01", skill_res["skill_name"], "AIMLEngineer")
    workflow = runner.execute_workflow()
    assert workflow["status"] == "SUCCESS"
    assert "NANO-GPT-01" in workflow["completed_steps"]


def test_git_nexus_integration():
    """GitNexusEngine now runs REAL git subprocess calls against an actual repo path."""
    from orchestrator.integrations import GitNexusEngine
    nexus = GitNexusEngine()

    sync_res = nexus.sync_multi_remotes(".")
    assert sync_res["status"] in ("ALL_REMOTES_SYNCHRONIZED", "SYNC_DRIFT_DETECTED", "NO_REMOTES_CONFIGURED")
    assert sync_res["latest_commit_hash"]  # real HEAD hash, non-empty

    health_res = nexus.audit_repository_health(".")
    assert health_res["status"] in ("HEALTHY", "NEEDS_ATTENTION", "UNHEALTHY")
    assert isinstance(health_res["repo_health_score"], float)
    assert isinstance(health_res["uncommitted_changes"], int)

    board_res = nexus.list_pr_issue_nexus()
    assert board_res["unified_board_status"] == "SYNCHRONIZED"


def test_playwright_moderator_integration(tmp_path):
    """PlaywrightVisualAuditor now runs a REAL headless Chromium and real Pillow pixel-diff."""
    from orchestrator.integrations import PlaywrightVisualAuditor, PlaywrightNotAvailableError

    try:
        moderator = PlaywrightVisualAuditor()
    except PlaywrightNotAvailableError as e:
        pytest.skip(f"playwright/chromium not installed: {e}")

    good_html = "<html><head><meta name='viewport' content='width=device-width'></head><body><h1>Welcome</h1></body></html>"
    res = moderator.run_ui_moderation(good_html)
    assert res["status"] == "APPROVED"
    assert res["visual_qa_score"] == 100.0
    assert res["layout_overflow_detected"] is False

    bad_html = "<html><body style='margin:0'><div style='color:#999;background:#aaa'>low contrast</div><div style='width:3000px;height:10px;background:red'></div></body></html>"
    bad_res = moderator.run_ui_moderation(bad_html)
    assert bad_res["status"] == "REJECTED"
    assert bad_res["layout_overflow_detected"] is True

    from PIL import Image
    base_path, cand_path = tmp_path / "baseline.png", tmp_path / "candidate.png"
    Image.new("RGB", (50, 50), color=(0, 0, 255)).save(base_path)
    Image.new("RGB", (50, 50), color=(0, 0, 255)).save(cand_path)

    diff = moderator.pixel_diff(str(base_path), str(cand_path))
    assert diff["status"] == "VISUAL_MATCH_PASSED"
    assert diff["regression_detected"] is False


def test_omniroute_gateway_integration():
    from orchestrator.integrations import OmniRouteGateway
    gateway = OmniRouteGateway()

    # Catalog validation
    catalog = gateway.get_catalog()
    assert catalog["status"] == "ONLINE"
    assert catalog["providers_total"] == 352
    assert catalog["free_tiers_total"] == 154
    assert catalog["models_total"] == 1240
    assert "Kimi" in catalog["families"]
    assert "DeepSeek" in catalog["families"]

    # Normal routing with RTK + Caveman compression
    prompt = "Please kindly make sure to analyze the database cluster thoroughly."
    route_res = gateway.route_request(prompt, model_preference="deepseek-v3", optimize_tokens=True)
    assert route_res["status"] == "ROUTED_OPTIMAL"
    assert route_res["provider"] == "deepseek"
    assert route_res["fallback_applied"] is False
    assert route_res["compression"]["saved_tokens"] > 0
    assert route_res["compression"]["saved_tokens_percentage"] >= 15.0

    # Quota-Aware Auto-Fallback on 429 quota exhaustion
    fallback_res = gateway.route_request("Review security", model_preference="claude-3-5-sonnet", quota_exhausted=True)
    assert fallback_res["status"] == "AUTO_FALLBACK_TRIGGERED"
    assert fallback_res["fallback_applied"] is True
    assert fallback_res["provider"] == "deepseek"


def test_external_ecosystem_hub():
    hub = ExternalEcosystemHub()
    status = hub.get_status()

    assert status["overall_status"] == "ALL_INTEGRATED"
    assert status["public_apis_loaded"] == 0  # not loaded until .load() is called
    assert status.get("openclaw_status") == "READY (real file scan, templated refinement)"
    assert status.get("taste_skill_status") == "READY (curated guidelines + real contrast math)"
    assert status.get("chatdev_status") == "READY (simulated)"
    assert status.get("rtk_token_compressor_status") == "READY (real text dedup)"
    assert status.get("karpathy_skills_status") == "READY"
    assert status.get("git_nexus_status") == "READY (real git operations)"
    assert status.get("playwright_moderator_status", "").startswith(("READY", "UNAVAILABLE"))
    assert status.get("omniroute_status") == "READY"
    assert status.get("omniroute_providers_count") == 352
    assert status.get("omniroute_free_tiers_count") == 154
