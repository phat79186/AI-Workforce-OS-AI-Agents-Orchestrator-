"""Layer 4: AI Workforce Registry supporting Seniority Tiers, Candidate Ranking, Budgeting, and Performance Feedback Loops."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from workforce.budget import WorkforceBudget
from workforce.employee import AIEmployee, SeniorityLevel
from workforce.ranking import CandidateRanker


class AIWorkforceRegistry:
    """Registry managing AI employee recruitment, candidate ranking, performance tracking, and budget enforcement."""

    def __init__(self, budget: Optional[WorkforceBudget] = None) -> None:
        self._employees: Dict[str, AIEmployee] = {}
        self.budget = budget or WorkforceBudget()
        self.ranker = CandidateRanker()
        self._active_concurrent_count = 0
        self._register_default_workforce()

    def _register_default_workforce(self) -> None:
        """Register default tiered AI employees."""
        self.register(
            AIEmployee(
                employee_id="EMP-01",
                name="JuniorCoder",
                role="Software Engineer",
                department="software_engineering",
                provider_name="ollama-qwen2.5-coder:7b",
                seniority=SeniorityLevel.JUNIOR,
                skills=["Python", "JavaScript", "Bugfix"],
                cost_tier="Free",
            )
        )
        self.register(
            AIEmployee(
                employee_id="EMP-02",
                name="SeniorArchitect",
                role="Senior Architect",
                department="software_engineering",
                provider_name="ollama-qwen2.5-coder:7b",
                seniority=SeniorityLevel.SENIOR,
                skills=["Python", "Architecture", "Refactoring", "Design Patterns"],
                cost_tier="Free",
            )
        )
        self.register(
            AIEmployee(
                employee_id="EMP-03",
                name="SecuritySpecialist",
                role="Security Specialist",
                department="software_engineering",
                provider_name="ollama-qwen2.5-coder:7b",
                seniority=SeniorityLevel.SPECIALIST,
                skills=["Security", "Vulnerability Audit", "Auth", "Encryption"],
                cost_tier="Free",
            )
        )
        self.register(
            AIEmployee(
                employee_id="EMP-04",
                name="Researcher",
                role="Research Analyst",
                department="research",
                provider_name="ollama-qwen2.5-coder:7b",
                seniority=SeniorityLevel.MID,
                skills=["Web Research", "RAG", "Obsidian Publishing", "Summarization"],
                cost_tier="Free",
            )
        )

    def register(self, employee: AIEmployee) -> None:
        """Register an AI employee into the workforce."""
        self._employees[employee.employee_id] = employee

    def get_employee(self, employee_id: str) -> Optional[AIEmployee]:
        """Get employee by ID."""
        return self._employees.get(employee_id)

    def recruit(
        self, *skills: Any, task_complexity: int = 3
    ) -> Optional[AIEmployee]:
        """Recruit best candidate using CandidateRanker matching and budget validation."""
        if not self.budget.validate_recruitment(len(self._employees), self._active_concurrent_count):
            return None

        candidates = list(self._employees.values())
        if not candidates:
            return None

        required_skills: List[str] = []
        if skills:
            if len(skills) == 1 and isinstance(skills[0], (list, tuple, set)):
                required_skills = [str(s) for s in skills[0]]
            else:
                skills_list = list(skills)
                if isinstance(skills_list[-1], int):
                    task_complexity = skills_list.pop()
                required_skills = [str(s) for s in skills_list]

        ranked = self.ranker.rank_candidates(candidates, required_skills, task_complexity)
        best_candidate, match_score = ranked[0]
        return best_candidate

    def evaluate_and_update(
        self,
        employee_id: str,
        success: bool,
        test_passed: bool,
        review_passed: bool,
        duration_sec: float,
    ) -> Optional[AIEmployee]:
        """Performance Feedback Loop: Update employee dynamic metrics after task run."""
        emp = self.get_employee(employee_id)
        if emp:
            emp.metrics.update(
                success=success,
                test_passed=test_passed,
                review_passed=review_passed,
                duration_sec=duration_sec,
            )
        return emp

    def list_employees(self, department: Optional[str] = None) -> List[AIEmployee]:
        """List employees, optionally filtered by department."""
        if not department:
            return list(self._employees.values())
        return [e for e in self._employees.values() if e.department == department]
