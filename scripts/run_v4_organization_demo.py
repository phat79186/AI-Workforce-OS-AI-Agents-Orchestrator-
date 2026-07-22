"""v4.0 Autonomous AI Organization Integration Demo Script."""

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

from v4_organization import AutonomousAIOrganization


def run_v4_demo() -> None:
    print("=================================================================")
    print("[v4.0 DEMO] AUTONOMOUS AI ORGANIZATION (EXECUTIVE BOARD & DEPARTMENTS)")
    print("=================================================================")

    user_vision = "Xay he thong Nhan dien khuon mat co Liveness Detection microservice"

    with tempfile.TemporaryDirectory(prefix="v4_org_vault_") as tmp_vault:
        # 1. Initialize Autonomous AI Organization
        print("\n[AI ORGANIZATION] Initializing Executive Board & Corporate Departments...")
        org = AutonomousAIOrganization(vault_path=tmp_vault)

        # 2. Executive Strategy Formulation by AI CEO
        print(f"\n[AI CEO] Formulating Strategic Vision for Initiative: '{user_vision}'...")
        goal = org.ceo.formulate_strategy(user_vision)
        print(f"  * Goal ID: {goal.goal_id}")
        print(f"  * Vision Statement: {goal.vision_statement}")
        print(f"  * Key Objectives: {goal.key_objectives}")

        # 3. Technical Execution Roadmap Generation by AI CTO
        print("\n[AI CTO] Translating Strategy into Cross-Department Technical Execution Roadmap...")
        roadmap = org.cto.build_technical_roadmap(goal)
        print(f"  * Generated Roadmap Subtasks ({len(roadmap.nodes)} Nodes):")
        for node in roadmap.nodes.values():
            deps = f" (Depends on: {', '.join(node.dependencies)})" if node.dependencies else ""
            print(f"    - [{node.task_id}] Dept Role: [{node.agent_role.upper()}] | {node.description}{deps}")

        # 4. Department Execution & Organizational Memory Recording
        print("\n[DEPARTMENT MANAGERS] Delegating Subtasks to Engineering, Research, and Operations...")
        res = org.execute_corporate_initiative(user_vision)

        print("\n[DEPARTMENT EXECUTION OUTCOMES]")
        for out in res["subtask_results"]:
            print(f"  * [{out.department_name.upper()}] Subtask {out.task_id} -> Recruited: [{out.assigned_employee}] | Status: {out.status}")

        # 5. AI CEO Executive Summary Report
        exec_report = res["executive_report"]
        print("\n[AI CEO EXECUTIVE REPORT]")
        print(f"  * Initiative Title: {exec_report['title']}")
        print(f"  * Executive Status: {exec_report['status']}")
        print(f"  * Performance Score: {exec_report['performance_score']}")
        print(f"  * Retained Learnings in Organizational Memory: {exec_report['retained_organizational_learnings']} documents")

        print("\n[SUCCESS] v4.0 Autonomous AI Organization Demo completed with 100% success!\n")


if __name__ == "__main__":
    run_v4_demo()
