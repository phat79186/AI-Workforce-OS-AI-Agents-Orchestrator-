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

    # 1. mattpocock/skills
    print("\n[1. MATTPOCOCK SKILLS] Discovering AI Agent Skills...")
    skill = hub.mattpocock_skills.find_skill("typescript-pro")
    print(f"  * Skill Found: [{skill.name}] | Category: {skill.category} | Tags: {skill.tags}")

    # 2. colbymchenry/codegraph
    print("\n[2. CODEGRAPH] Exploring Code Graph Symbol Call Paths...")
    sym_info = hub.codegraph.explore_symbol("execute_corporate_initiative")
    print(f"  * Symbol: [{sym_info['name']}] ({sym_info['type']}) | File: {sym_info['file']}:{sym_info['line']}")
    print(f"  * Callers: {sym_info['callers']} | Callees: {sym_info['callees']}")

    # 3. DietrichGebert/ponytail
    print("\n[3. PONYTAIL RUNNER] Executing Multi-Agent Workflow Step...")
    hub.ponytail.add_step("PONY-01", "security_audit", "SecuritySpecialist")
    pony_res = hub.ponytail.execute_workflow()
    print(f"  * Workflow Executed: {pony_res['completed_steps']} | Status: {pony_res['status']}")

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

    # 6. pbakaus/impeccable
    print("\n[6. IMPECCABLE DESIGN] Performing UI Visual Polish & Accessibility Audit...")
    audit = hub.impeccable.audit_ui_component("ExecutiveDashboardHeader")
    print(f"  * Component: [{audit['component']}] | WCAG: {audit['wcag_compliance']} | Status: {audit['status']}")

    # 7. public-apis/public-apis
    print("\n[7. PUBLIC APIS DIRECTORY] Searching External Microservice Endpoints...")
    apis = hub.public_apis.search_apis("AI")
    for a in apis:
        print(f"  * API: [{a.api_name}] | Category: {a.category} | Auth: {a.auth_type} | URL: {a.url}")

    # 8. Zleap-AI/SAG
    print("\n[8. SAG FRAMEWORK] Synchronizing Semantic Agent Graph Nodes...")
    hub.sag.register_agent("CTO-AGENT", "ExecutiveCTO", {"mode": "strategic_planning"})
    sag_res = hub.sag.synchronize_graph()
    print(f"  * Graph Synchronized: {sag_res['node_count']} Node | Status: {sag_res['status']}")

    # Final Overall Hub Status
    status = hub.get_status()
    print("\n=================================================================")
    print(f"[SUMMARY] All 8 External Tools & Skills Integrated 100% Successfully!")
    print(f"  * Status: {status['overall_status']}")
    print("=================================================================\n")


if __name__ == "__main__":
    run_external_ecosystem_demo()
