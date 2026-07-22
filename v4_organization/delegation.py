"""AI-to-AI Delegation Engine for multi-tier executive and director level delegation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from workforce import AIWorkforceRegistry, AIEmployee


@dataclass
class DelegationNode:
    """Represents a delegation node in the AI-to-AI delegation tree."""

    manager_title: str
    subordinate_title: str
    department: str
    delegated_task: str
    assigned_employee: str


class AIToAIDelegator:
    """Engine executing multi-tier AI-to-AI delegation (CEO -> CTO -> Directors -> Team Specialists)."""

    def __init__(self, workforce: AIWorkforceRegistry) -> None:
        self.workforce = workforce

    def delegate_task(
        self, manager_title: str, subordinate_title: str, department: str, task_description: str, required_skills: List[str]
    ) -> DelegationNode:
        """Delegate task from a higher-level AI Manager/Director to a subordinate AI Specialist."""
        emp = self.workforce.recruit(required_skills, task_complexity=4)
        emp_name = emp.name if emp else "DefaultSpecialist"

        return DelegationNode(
            manager_title=manager_title,
            subordinate_title=subordinate_title,
            department=department,
            delegated_task=task_description,
            assigned_employee=emp_name,
        )

    def execute_delegation_tree(self, user_vision: str) -> List[DelegationNode]:
        """Execute full multi-tier AI-to-AI delegation tree across executive directors and department managers."""
        nodes: List[DelegationNode] = []

        # 1. CTO -> Research Director delegation
        nodes.append(
            self.delegate_task(
                manager_title="AI CTO",
                subordinate_title="Research Director",
                department="research",
                task_description=f"Conduct technology survey & state-of-the-art research for {user_vision}",
                required_skills=["Web Research", "RAG"],
            )
        )

        # 2. CTO -> Security Director delegation
        nodes.append(
            self.delegate_task(
                manager_title="AI CTO",
                subordinate_title="Security Director",
                department="security",
                task_description="Formulate threat model & security compliance standards",
                required_skills=["Security", "Vulnerability Audit"],
            )
        )

        # 3. CTO -> Engineering Manager delegation
        nodes.append(
            self.delegate_task(
                manager_title="AI CTO",
                subordinate_title="Engineering Manager",
                department="engineering",
                task_description="Build modular software architecture & backend logic",
                required_skills=["Python", "Architecture"],
            )
        )

        # 4. Engineering Manager -> Tester delegation
        nodes.append(
            self.delegate_task(
                manager_title="Engineering Manager",
                subordinate_title="QA Lead",
                department="engineering",
                task_description="Execute automated regression test suite & validation",
                required_skills=["Python", "Bugfix"],
            )
        )

        # 5. CTO -> DevOps Director delegation
        nodes.append(
            self.delegate_task(
                manager_title="AI CTO",
                subordinate_title="DevOps Manager",
                department="operations",
                task_description="Deploy containerized microservice & CI/CD pipeline",
                required_skills=["Docker", "CI/CD"],
            )
        )

        return nodes
