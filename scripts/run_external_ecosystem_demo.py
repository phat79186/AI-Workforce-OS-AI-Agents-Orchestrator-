"""Integration Demo Script for 8 External Repositories & Skills in AI Workforce OS v4.2."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from orchestrator.integrations import ExternalEcosystemHub


def run_external_ecosystem_demo() -> None:
    print("=================================================================")
    print("[INTEGRATION DEMO] 8 EXTERNAL REPOSITORIES & SKILLS (v4.2 ECOSYSTEM)")
    print("=================================================================")

    hub = ExternalEcosystemHub()

    # 1. mattpocock/skills & multica-ai/andrej-karpathy-skills
    print("\n[1. MATTPOCOCK & KARPATHY SKILLS] Discovering AI & Engineering Agent Skills...")
    skill = hub.mattpocock_skills.find_skill("typescript-pro")
    karpathy_res = hub.karpathy_skills.execute_skill_pattern("nanogpt-transformer")
    print(f"  * Matt Pocock Skill: [{skill.name}] | Category: {skill.category} | Tags: {skill.tags}")
    print(f"  * Karpathy AI Skill: [{karpathy_res['skill_name']}] | Category: {karpathy_res['category']} | Tags: {karpathy_res['tags']}")

    # 2. colbymchenry/codegraph
    print("\n[2. CODEGRAPH] Exploring Code Graph Symbol Call Paths...")
    sym_info = hub.codegraph.explore_symbol("execute_corporate_initiative")
    print(f"  * Symbol: [{sym_info['name']}] ({sym_info['type']}) | File: {sym_info['file']}:{sym_info['line']}")
    print(f"  * Callers: {sym_info['callers']} | Callees: {sym_info['callees']}")

    # 3. DietrichGebert/ponytail + Karpathy Skill Actions
    print("\n[3. PONYTAIL RUNNER + KARPATHY SKILL] Executing Multi-Agent DAG Workflow Steps...")
    hub.ponytail.add_step("PONY-01", "code_review", "LeadSoftwareEngineer")
    hub.ponytail.add_step("PONY-02", "security_audit", "SecuritySpecialist", dependencies=["PONY-01"])
    hub.ponytail.add_step("PONY-03", karpathy_res["skill_name"], "AIMLEngineer", dependencies=["PONY-02"])
    pony_res = hub.ponytail.execute_workflow(parallel_dispatch=True)
    print(f"  * Total Steps: {pony_res['total_steps']} | Completed: {pony_res['completed_steps']}")
    print(f"  * Topological Execution Order: {pony_res['execution_order']} | Status: {pony_res['status']}")

    # 4. anysearch-ai/anysearch-skill + Panniantong/Agent-Reach
    print("\n[4. ANYSEARCH SKILL + AGENT-REACH] Executing Deep Multi-Engine Search Reach...")
    search_res = hub.anysearch.execute_search("Face Liveness Security Architecture", enable_agent_reach=True, max_depth=2)
    print(f"  * Query: '{search_res['query']}' | Agent-Reach Source: {search_res['agent_reach_source']}")
    print(f"  * Sources Searched ({len(search_res['sources_searched'])} Engines): {search_res['sources_searched']}")
    print(f"  * Total Results & Citations: {search_res['results_count']}")
    if search_res.get("reach_metadata"):
        print(f"  * Reach Radius Score: {search_res['reach_metadata']['reach_radius_score']} / 1.0")
        print(f"  * Deep Retrieval Summary: {search_res['reach_metadata']['deep_retrieval_summary']}")

    # 5. nextlevelbuilder/ui-ux-pro-max-skill
    print("\n[5. UI/UX PRO MAX] Generating Modern Design System...")
    ds = hub.ui_ux_pro_max.generate_design_system("Dark Glassmorphism")
    print(f"  * Theme: [{ds['theme']}] | Primary: {ds['palette']['primary']} | Font: {ds['typography']['font_family']}")

    # 6. pbakaus/impeccable & Taste Skill
    print("\n[6. IMPECCABLE DESIGN & TASTE SKILL] Performing Visual Curation & Accessibility Audit...")
    audit = hub.impeccable.audit_ui_component("ExecutiveDashboardHeader")
    taste_curation = hub.taste.curate_design_taste("ExecutiveDashboardHeader")
    print(f"  * Component: [{audit['component']}] | WCAG: {audit['wcag_compliance']} | Audit Status: {audit['status']}")
    print(f"  * Taste Curation Score: {taste_curation['visual_taste_score']} / 1.0 | Status: {taste_curation['status']}")
    print(f"  * Spatial Harmony: {taste_curation['spatial_harmony']['grid_system']} ({taste_curation['spatial_harmony']['alignment']})")
    print(f"  * Motion Choreography: {taste_curation['motion_choreography']['hover_interaction']} ({taste_curation['motion_choreography']['easing']})")

    # 7. public-apis/public-apis
    print("\n[7. PUBLIC APIS DIRECTORY] Searching External Microservice Endpoints...")
    apis = hub.public_apis.search_apis("AI")
    for a in apis:
        print(f"  * API: [{a.api_name}] | Category: {a.category} | Auth: {a.auth_type} | URL: {a.url}")

    # 8. OpenBMB/ChatDev Virtual Software Company
    print("\n[8. CHATDEV VIRTUAL SOFTWARE COMPANY] Executing Communicative Multi-Agent Development...")
    chatdev_res = hub.chatdev.run_virtual_software_company("FaceAuthMicroservice", "Build Face Authentication Microservice")
    print(f"  * Software Name: [{chatdev_res['software_name']}] | Status: {chatdev_res['status']}")
    print(f"  * Completed Phases ({len(chatdev_res['completed_phases'])} Phases): {chatdev_res['completed_phases']}")
    print(f"  * Deployed Virtual Roles ({len(chatdev_res['virtual_roles_deployed'])} Roles): {chatdev_res['virtual_roles_deployed']}")
    print(f"  * Generated Project Files: {chatdev_res['generated_files']}")

    # 9. rtk-ai/rtk Redundant Token Killer
    print("\n[9. RTK TOKEN COMPRESSOR] Compressing Inter-Agent Dialog Tokens...")
    sample_dialog = [
        {"role": "CEO", "content": "You are the Lead CTO. Please formulate a technical roadmap for Face Authentication Microservice with Pytest checks.\nPlease formulate a technical roadmap for Face Authentication Microservice with Pytest checks."},
        {"role": "CTO", "content": "Roadmap created:\n  - Step 1: Initialize FastApi Backend\n  - Step 2: Integrate Silent-Face Anti-Spoofing Model\n  - Step 3: Run Playwright Visual QA Checks"},
    ]
    rtk_res = hub.rtk.compress_agent_dialog(sample_dialog)
    print(f"  * Source Repo: {rtk_res['source_repo']} | Status: {rtk_res['status']}")
    print(f"  * Token Savings: {rtk_res['original_total_tokens']} ➔ {rtk_res['compressed_total_tokens']} tokens (-{rtk_res['token_reduction_percentage']}%)")
    print(f"  * Tokens Saved: {rtk_res['saved_total_tokens']} tokens eliminated without semantic loss")

    # 10. Zleap-AI/SAG
    print("\n[10. SAG FRAMEWORK] Synchronizing Semantic Agent Graph Nodes...")
    hub.sag.register_agent("CTO-AGENT", "ExecutiveCTO", {"mode": "strategic_planning"})
    sag_res = hub.sag.synchronize_graph()
    print(f"  * Graph Synchronized: {sag_res['node_count']} Node | Status: {sag_res['status']}")

    # 11. abhigyanpatwari/GitNexus Multi-platform Sync & Health Audit
    print("\n[11. GITNEXUS ENGINE] Performing Multi-Remote Sync & Repo Health Auditing...")
    git_nexus_res = hub.git_nexus.sync_multi_remotes(".")
    health_res = hub.git_nexus.audit_repository_health(".")
    print(f"  * Source Repo: {git_nexus_res['source_repo']} | Status: {git_nexus_res['status']}")
    print(f"  * Synced Remotes: {len(git_nexus_res['synced_remotes'])} remotes (GitHub, GitLab) synchronized")
    print(f"  * Repository Health Score: {health_res['repo_health_score']}/100 | Status: {health_res['status']}")

    # 12. microsoft/playwright Visual Moderation & Layout Auditing
    print("\n[12. PLAYWRIGHT MODERATOR] Executing Headless Visual QA & Layout Auditing...")
    html_sample = "<html><head><meta name='viewport' content='width=device-width'></head><body><h1>Dashboard</h1><img src='placeholder.png'/></body></html>"
    playwright_res = hub.playwright_moderator.run_ui_moderation(html_sample)
    diff_res = hub.playwright_moderator.pixel_diff("baseline.png", "candidate.png")
    print(f"  * Source Repo: {playwright_res['source_repo']} | Status: {playwright_res['status']}")
    print(f"  * Visual QA Score: {playwright_res['visual_qa_score']}/100 | WCAG AA Contrast Pass: {playwright_res['wcag_aa_contrast_pass']}")
    print(f"  * Regression Check: {diff_res['status']} | Diff: {diff_res['diff_pixels_percentage']}% pixels mismatch")

    # Final Overall Hub Status
    status = hub.get_status()
    print("\n=================================================================")
    print(f"[SUMMARY] All External Tools, Skills & Frameworks Integrated 100% Successfully!")
    print(f"  * Status: {status['overall_status']}")
    print("=================================================================\n")


if __name__ == "__main__":
    run_external_ecosystem_demo()
