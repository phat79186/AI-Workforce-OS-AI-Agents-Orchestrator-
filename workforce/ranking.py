"""Candidate Ranking engine for matching task requirements to AI employees."""

from __future__ import annotations

from typing import List, Optional, Tuple
from workforce.employee import AIEmployee, SeniorityLevel


class CandidateRanker:
    """Ranks candidate AI employees for recruitment using multi-variable Match Score."""

    SENIORITY_WEIGHTS = {
        SeniorityLevel.INTERN: 1,
        SeniorityLevel.JUNIOR: 2,
        SeniorityLevel.MID: 3,
        SeniorityLevel.SENIOR: 4,
        SeniorityLevel.SPECIALIST: 5,
    }

    def calculate_match_score(
        self, employee: AIEmployee, required_skills: List[str], task_complexity: int = 3
    ) -> float:
        """Calculate Candidate Match Score based on Skills, Seniority, Reliability, and Success Rate."""
        req_skills_lower = {s.lower() for s in required_skills}
        emp_skills_lower = {s.lower() for s in employee.skills}

        # 1. Skill Match Score (0.0 to 5.0)
        overlap = len(req_skills_lower.intersection(emp_skills_lower))
        skill_score = overlap * 2.0

        # 2. Seniority Match Score
        emp_seniority_weight = self.SENIORITY_WEIGHTS.get(employee.seniority, 3)
        seniority_diff = abs(emp_seniority_weight - task_complexity)
        seniority_score = max(0.0, 3.0 - seniority_diff)

        # 3. Dynamic Reliability Score & Success Rate (0.0 to 2.0)
        reliability = employee.metrics.reliability_score * 2.0

        # Total Match Score
        return round(skill_score + seniority_score + reliability, 2)

    def rank_candidates(
        self, candidates: List[AIEmployee], required_skills: List[str], task_complexity: int = 3
    ) -> List[Tuple[AIEmployee, float]]:
        """Rank candidate AI employees descending by match score."""
        ranked = [
            (emp, self.calculate_match_score(emp, required_skills, task_complexity))
            for emp in candidates
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
