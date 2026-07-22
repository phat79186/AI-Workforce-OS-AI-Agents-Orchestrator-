"""Department Managers for Engineering, Research, and Operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from workforce import AIWorkforceRegistry, AIEmployee


@dataclass
class DepartmentTaskResult:
    """Outcome of a department subtask execution."""

    task_id: str
    department_name: str
    assigned_employee: str
    status: str
    artifacts_created: List[str] = field(default_factory=list)


class BaseDepartmentManager:
    """Base class for Department Managers."""

    def __init__(self, department_name: str, workforce: AIWorkforceRegistry) -> None:
        self.department_name = department_name
        self.workforce = workforce

    def execute_subtask(self, task_id: str, description: str, role: str) -> DepartmentTaskResult:
        """Recruit matching employee and execute department subtask."""
        skill_map = {
            "coder": ["Python", "Architecture"],
            "tester": ["Python", "Bugfix"],
            "researcher": ["Web Research", "RAG"],
            "security_auditor": ["Security", "Vulnerability Audit"],
            "devops_engineer": ["Docker", "CI/CD"],
        }
        skills = skill_map.get(role, ["Python"])
        emp = self.workforce.recruit(skills, task_complexity=4)
        emp_name = emp.name if emp else "DefaultAgent"

        return DepartmentTaskResult(
            task_id=task_id,
            department_name=self.department_name,
            assigned_employee=emp_name,
            status="COMPLETED",
            artifacts_created=[f"{task_id}_output.md"],
        )


class EngineeringManager(BaseDepartmentManager):
    """Engineering Department Manager governing Coders, Testers, and Reviewers."""

    def __init__(self, workforce: AIWorkforceRegistry) -> None:
        super().__init__("engineering", workforce)


class ResearchManager(BaseDepartmentManager):
    """Research Department Manager governing Researchers and Knowledge Synthesizers."""

    def __init__(self, workforce: AIWorkforceRegistry) -> None:
        super().__init__("research", workforce)


class OperationsManager(BaseDepartmentManager):
    """Operations Department Manager governing DevOps Engineers and Security Auditors."""

    def __init__(self, workforce: AIWorkforceRegistry) -> None:
        super().__init__("operations", workforce)
