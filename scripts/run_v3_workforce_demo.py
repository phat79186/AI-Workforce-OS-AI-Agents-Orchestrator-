"""v3.0 AI Workforce Ecosystem Integration Demo Script."""

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

from v3_orchestrator import V3WorkforceManager
from domains import (
    SoftwareEngineeringDomain,
    ResearchDomain,
    DevOpsDomain,
    DataAnalysisDomain,
    ContentCreationDomain,
    DocumentationDomain,
    KnowledgeManagementDomain,
)


def run_v3_demo() -> None:
    print("=================================================================")
    print("[v3.0 DEMO] AI WORKFORCE ECOSYSTEM (4-LAYER OS)")
    print("=================================================================")

    with tempfile.TemporaryDirectory(prefix="v3_vault_") as tmp_vault:
        # 1. Initialize v3.0 Workforce Manager
        print("\n[LAYER 1: KERNEL] Initializing AI OS Kernel & Event Bus...")
        manager = V3WorkforceManager(vault_path=tmp_vault)

        # 2. Display Layer 2 Domain Ecosystems
        print("\n[LAYER 2: DOMAIN ECOSYSTEMS] Registering Department Ecosystems...")
        domains = [
            SoftwareEngineeringDomain(),
            ResearchDomain(),
            DevOpsDomain(),
            DataAnalysisDomain(),
            ContentCreationDomain(),
            DocumentationDomain(),
            KnowledgeManagementDomain(),
        ]
        for d in domains:
            print(f"  * Department: [{d.metadata.name.upper()}] | Roles: {d.get_roles()} | Workflows: {d.get_workflows()}")

        # 3. Layer 3: Shared Knowledge Bridge - Research Agent Teaches Coding Agent
        print("\n[LAYER 3: SHARED KNOWLEDGE BRIDGE] Research Agent publishing knowledge to Obsidian Vault...")
        pub_path = manager.knowledge_bridge.publish_research(
            title="Face Liveness ADR",
            content="Architecture for passive liveness detection using anti-spoofing models and challenge-response validation.",
            category="Security",
        )
        print(f"  * Published Knowledge File: {pub_path}")

        # 4. Layer 4: AI Workforce Recruitment by Skill
        print("\n[LAYER 4: AI WORKFORCE] Recruiting AI Employees based on required task skills...")
        recruited_emp = manager.workforce.recruit("Python", "Debugging")
        print(f"  * Employee Recruited: [{recruited_emp.name}] | Role: {recruited_emp.role} | Provider: {recruited_emp.provider_name} | Rating: {recruited_emp.performance_rating}")

        # 5. End-to-End Task Execution
        print("\n[v3.0 EXECUTION] Executing cross-layer task...")
        task_prompt = "Implement Face Liveness feature with anti-spoofing unit tests"
        res = manager.execute_task(task_prompt, required_skills=["Python", "Testing"])

        print("\n[v3.0 EXECUTION RESULT]")
        print(f"  * Task ID: {res['task_id']}")
        print(f"  * Employee Assigned: {res['assigned_employee']} ({res['employee_role']})")
        print(f"  * Provider Selected: {res['provider']}")
        print(f"  * Allowed Tools: {res['allowed_tools']}")
        print(f"  * Cross-Agent Knowledge Docs Retrieved: {res['retrieved_context_count']}")
        print(f"  * Status: {res['status'].upper()}")

        print("\n[SUCCESS] v3.0 AI Workforce Ecosystem 4-Layer Demo completed successfully!\n")


if __name__ == "__main__":
    run_v3_demo()
