"""v4.1 AI-to-AI Delegation & Cross-Project Organizational Memory Learning Demo Script."""

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

from v4_organization import AutonomousAIOrganization, OrganizationalLearningRecord


def run_v4_1_demo() -> None:
    print("=================================================================")
    print("[v4.1 DEMO] AI-TO-AI DELEGATION & ORGANIZATIONAL MEMORY LEARNING")
    print("=================================================================")

    with tempfile.TemporaryDirectory(prefix="v4_1_org_vault_") as tmp_vault:
        # 1. Initialize Autonomous AI Organization
        print("\n[AI ORGANIZATION] Initializing AI Executive Leadership & Organizational Memory...")
        org = AutonomousAIOrganization(vault_path=tmp_vault)

        # 2. AI-to-AI Delegation Tree Showcase
        print("\n[AI-TO-AI DELEGATION TREE] Multi-Tier Executive & Director Delegation:")
        nodes = org.delegator.execute_delegation_tree("Nen tang Nhan dien khuon mat co Liveness Detection")
        for n in nodes:
            print(f"  * [{n.manager_title}] ──► [{n.subordinate_title}] ({n.department.upper()}) | Recruited: [{n.assigned_employee}]")
            print(f"    Task: '{n.delegated_task}'")

        # 3. Project 1 Execution: Face Recognition Platform v1
        proj1_name = "Face Recognition Platform v1"
        print(f"\n[PROJECT 1 EXECUTION] Executing Initiative: '{proj1_name}'...")
        res1 = org.execute_corporate_initiative(proj1_name)

        print(f"  * Project 1 Status: {res1['executive_report']['status']}")
        print(f"  * Subtasks Completed: {res1['total_subtasks']}")

        # Save Organizational Learnings from Project 1
        rec1 = OrganizationalLearningRecord(
            project_name=proj1_name,
            lessons_learned=[
                "Sử dụng mô hình passive liveness thay vì active prompt để giảm trễ giao diện",
                "Luôn cô lập môi trường test trong Security Sandbox trước khi deploy",
            ],
            architecture_decisions=[
                "ADR-01: Kiến trúc Microservices giao tiếp qua REST API & gRPC",
            ],
            security_findings=[
                "SEC-01: Kiểm toán tính hợp lệ của khung hình ảnh chống giả mạo (Anti-Spoofing Check)",
            ],
            failed_approaches=[
                "Tránh kiểm tra assertion ở Client-side mà không có xác thực chữ ký ở Server-side",
            ],
            successful_patterns=[
                "Tự động chạy Pytest suite 100% GREEN trước khi cấp phép commit Git",
            ],
        )
        saved_path = org.memory.save_project_learnings(rec1)
        print(f"  * Saved Project Learnings to Organizational Memory: {saved_path}")

        # 4. Project 2 Execution: Face Liveness Microservice v2 (Learns from Project 1 History)
        proj2_name = "Face Liveness Microservice v2"
        print(f"\n[PROJECT 2 EXECUTION] Executing Initiative: '{proj2_name}'...")
        print("  [ORGANIZATIONAL MEMORY LOOKUP] Consulting past organizational experience & lessons learned...")

        past_learnings = org.memory.get_lessons_learned("Face Liveness anti-spoofing")
        print(f"  * Historical Learnings Found: {len(past_learnings)} documents retrieved")
        for idx, doc in enumerate(past_learnings, 1):
            print(f"    {idx}. [{doc['title']}] (Path: {doc['path']})")

        res2 = org.execute_corporate_initiative(proj2_name)

        print("\n[AI CEO EXECUTIVE REPORT - PROJECT 2]")
        print(f"  * Title: {res2['executive_report']['title']}")
        print(f"  * Status: {res2['executive_report']['status']}")
        print(f"  * Historical Lessons Consulted: {res2['previous_learnings_consulted']}")
        print(f"  * Performance Score: {res2['executive_report']['performance_score']}")

        print("\n[SUCCESS] v4.1 AI-to-AI Delegation & Organizational Memory Learning Demo completed with 100% success!\n")


if __name__ == "__main__":
    run_v4_1_demo()
