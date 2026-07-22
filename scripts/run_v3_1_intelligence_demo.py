"""v3.1 Workforce Intelligence & AI CTO Manager Integration Demo Script."""

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

from v3_orchestrator import AICTOManager, V3WorkforceManager
from workforce import AIEmployee, SeniorityLevel, WorkforceBudget


def run_v3_1_demo() -> None:
    print("=================================================================")
    print("[v3.1 DEMO] WORKFORCE INTELLIGENCE & AI CTO MANAGER")
    print("=================================================================")

    with tempfile.TemporaryDirectory(prefix="v3_1_vault_") as tmp_vault:
        # 1. Initialize AI CTO Manager
        print("\n[AI CTO MANAGER] Khoi tao AI CTO Manager & Task Planning Engine...")
        cto = AICTOManager(vault_path=tmp_vault)

        # 2. Decompose user request into Cross-Department Task DAG
        user_prompt = "Xay he thong nhan dien khuon mat co liveness detection"
        print(f"  * User Prompt: '{user_prompt}'")

        graph = cto.plan_project(user_prompt)
        print(f"\n[CROSS-DEPARTMENT TASK DAG] Dynamic Tasks Generated ({len(graph.nodes)} Subtasks):")
        for node in graph.nodes.values():
            deps = f" (Depends on: {', '.join(node.dependencies)})" if node.dependencies else ""
            print(f"  * [{node.task_id}] Role: [{node.agent_role.upper()}] | {node.description}{deps}")

        # 3. Dynamic AI Employee Recruitment via Candidate Ranking & Seniority
        print("\n[RECRUITMENT ENGINE] Recruiting AI Team via Candidate Ranking & Seniority Matching...")
        team = cto.recruit_team(graph)
        for task_id, emp in team.items():
            print(f"  * [{task_id}] -> Recruited: [{emp.name}] ({emp.seniority.value} {emp.role}) | Rating: {emp.metrics.reliability_score}")

        # 4. Performance Feedback Loop
        print("\n[PERFORMANCE FEEDBACK LOOP] Simulating Task Execution & Metric Updates...")
        recruited_emp = cto.workforce.get_employee("EMP-02")
        if recruited_emp:
            print(f"  * Initial [{recruited_emp.name}] Reliability: {recruited_emp.metrics.reliability_score}")

            # Record task runs
            cto.workforce.evaluate_and_update("EMP-02", success=True, test_passed=True, review_passed=True, duration_sec=4.2)
            cto.workforce.evaluate_and_update("EMP-02", success=True, test_passed=True, review_passed=True, duration_sec=3.8)

            print(f"  * Updated [{recruited_emp.name}] Tasks Completed: {recruited_emp.metrics.tasks_completed}")
            print(f"  * Updated [{recruited_emp.name}] Success Rate: {recruited_emp.metrics.success_rate * 100}%")
            print(f"  * Updated [{recruited_emp.name}] Dynamic Reliability Score: {recruited_emp.metrics.reliability_score}")

        # 5. Workforce Budget Limits
        print("\n[WORKFORCE BUDGET] Enforcing Resource Limits & Concurrency Caps...")
        budget = cto.workforce.budget
        print(f"  * Max Total Agents: {budget.max_total_agents}")
        print(f"  * Max Concurrent Agents: {budget.max_concurrent_agents}")
        print(f"  * Max Task Cost: ${budget.max_task_cost}")
        print(f"  * Max Execution Time: {budget.max_execution_time_sec}s")

        print("\n[SUCCESS] v3.1 Workforce Intelligence & AI CTO Manager Demo completed successfully!\n")


if __name__ == "__main__":
    run_v3_1_demo()
