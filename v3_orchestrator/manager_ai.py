"""AI Engineering Manager / CTO AI for cross-department task decomposition and team delegation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from orchestrator.core.dependency_graph import DependencyGraph, TaskNode
from shared_knowledge import KnowledgeBridge
from workforce import AIWorkforceRegistry, AIEmployee


class AICTOManager:
    """AI Engineering Manager (CTO AI) orchestrating cross-department AI teams."""

    def __init__(self, vault_path: Optional[str] = None) -> None:
        self.workforce = AIWorkforceRegistry()
        self.knowledge_bridge = KnowledgeBridge(vault_path=vault_path)

    def plan_project(self, high_level_prompt: str) -> DependencyGraph:
        """Decompose high-level request into a cross-department Task DAG."""
        graph = DependencyGraph()

        # Step 1: Research & Tech Survey
        graph.add_task("TASK-01-RESEARCH", f"Nghiên cứu kiến trúc cho: {high_level_prompt}", "researcher")

        # Step 2: Security & Architecture Analysis
        graph.add_task("TASK-02-SECURITY", "Phân tích lỗ hổng & Tiêu chuẩn bảo mật (Security Audit)", "security_auditor", dependencies=["TASK-01-RESEARCH"])
        graph.add_task("TASK-03-ARCH", "Thiết kế kiến trúc hệ thống (System Architecture)", "coder", dependencies=["TASK-01-RESEARCH"])

        # Step 3: Implementation
        graph.add_task("TASK-04-BACKEND", "Phát triển Backend logic & API", "coder", dependencies=["TASK-03-ARCH"])

        # Step 4: Verification & DevOps
        graph.add_task("TASK-05-TESTING", "Chạy automated unit & integration test", "tester", dependencies=["TASK-04-BACKEND"])
        graph.add_task("TASK-06-DEVOPS", "Đóng gói Docker & cấu hình deployment", "devops_engineer", dependencies=["TASK-05-TESTING"])
        graph.add_task("TASK-07-DOCS", "Tạo tài liệu API & Obsidian Vault ADR", "doc_writer", dependencies=["TASK-05-TESTING"])

        return graph

    def recruit_team(self, graph: DependencyGraph) -> Dict[str, AIEmployee]:
        """Recruit minimum necessary AI team for all tasks in graph within budget."""
        team: Dict[str, AIEmployee] = {}

        skill_map = {
            "researcher": ["Web Research", "RAG"],
            "security_auditor": ["Security", "Vulnerability Audit"],
            "coder": ["Python", "Architecture"],
            "tester": ["Python", "Bugfix"],
            "devops_engineer": ["Docker", "CI/CD"],
            "doc_writer": ["Obsidian Publishing", "Summarization"],
        }

        for node in graph.nodes.values():
            skills = skill_map.get(node.agent_role, ["Python"])
            emp = self.workforce.recruit(skills, task_complexity=4)
            if emp:
                team[node.task_id] = emp

        return team
