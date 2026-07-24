"""OpenClaw (openclaw/openclaw) Aegis V5.5 Context-Aware Prompt Processor Demo Script."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from providers.openclaw_provider import OpenClawProvider
from v4_organization import AutonomousAIOrganization


def run_openclaw_demo() -> None:
    print("=================================================================")
    print("[OPENCLAW AEGIS V5.5 DEMO] CONTEXT-AWARE PROMPT ENGINE")
    print("=================================================================")

    # 1. User inputs raw/brief prompt
    raw_user_input = "sửa UX UI"
    print(f"\n[USER INPUT] Raw Brief Input: \"{raw_user_input}\"")

    with tempfile.TemporaryDirectory(prefix="existing_project_repo_") as demo_repo:
        repo_path = Path(demo_repo)
        # Create an existing project theme file (e.g., Brand Color #ef4444)
        (repo_path / "tailwind.config.js").write_text(
            "module.exports = { theme: { extend: { colors: { brand: '#ef4444' } } } };", encoding="utf-8"
        )

        # 2. OpenClaw scans project context & refines raw prompt
        print("\n[OPENCLAW CONTEXT SCAN] Scanning project directory for existing design tokens...")
        claw = OpenClawProvider()
        processed = claw.refine_raw_prompt(raw_user_input, project_root=str(repo_path))

        print(f"  * Architecture: {processed['architecture'].upper()}")
        print(f"  * Prompt Optimizer Source: {processed['prompt_optimizer_source']} (Clarity Score: {processed['clarity_score']} / 1.0)")
        print(f"  * Theme Detection Status: {processed['context_scan']['theme_status']}")
        print(f"  * Palette Decision: {processed['context_scan']['palette_summary']}")
        print(f"  * Detected Domain: {processed['domain']}")
        print(f"  * Enriched Title: {processed['title']}")
        
        print("\n[LINSHENKX META-PROMPTING TRANSFORMATIONS]")
        print(f"  * System Role: {processed['optimization']['system_role']}")
        print("  * Applied Optimization Techniques:")
        for tech in processed['optimization']['optimization_techniques']:
            print(f"    - {tech}")
        print("  * Critical Negative Constraints:")
        for nc in processed['optimization']['negative_constraints']:
            print(f"    - {nc}")

        print("\n[STRATEGIC OBJECTIVES]")
        for obj in processed['objectives']:
            print(f"    - {obj}")
            
        print("\n[ASSIGNED PRIMARY LEAD AGENT (Anti-Role-Bloat)]")
        for role in processed['recommended_roles']:
            print(f"    - {role} (Per-Node Contract Checkpoint Enabled)")
            
        print("\n[HYBRID VISUAL QA TESTING CRITERIA]")
        for crit in processed['testing_criteria']:
            print(f"    - {crit}")

        # 3. AI Organization executes initiative using OpenClaw specification
        print("\n[AI ORGANIZATION] Passing OpenClaw specification to AI CEO & AI CTO...")
        org = AutonomousAIOrganization(vault_path=str(repo_path))

        res = org.execute_corporate_initiative(raw_user_input, use_openclaw=True)

        print("\n[AI CEO STRATEGIC PLAN]")
        print(f"  * Initiative Title: {res['goal'].title}")
        print(f"  * Vision Statement: {res['goal'].vision_statement}")
        print(f"  * Key Objectives Count: {len(res['goal'].key_objectives)}")

        print("\n[EXECUTIVE REPORT]")
        print(f"  * Status: {res['executive_report']['status']}")
        print(f"  * Performance Score: {res['executive_report']['performance_score']}")

    print("\n=================================================================")
    print("[SUCCESS] Aegis V5.5 OpenClaw Prompt Refinement Demo completed 100% successfully!")
    print("=================================================================\n")


if __name__ == "__main__":
    run_openclaw_demo()
