"""Layer 4: AI Employee profile definition with Seniority Levels and Dynamic Performance Metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SeniorityLevel(str, Enum):
    """Seniority levels for candidate ranking."""

    INTERN = "Intern"
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    SPECIALIST = "Specialist"


@dataclass
class PerformanceMetrics:
    """Dynamic metrics tracked per AI employee across execution history."""

    tasks_completed: int = 0
    success_count: int = 0
    test_pass_count: int = 0
    review_pass_count: int = 0
    total_time_sec: float = 0.0
    reliability_score: float = 1.0  # 0.0 to 1.0 dynamic score

    @property
    def success_rate(self) -> float:
        if self.tasks_completed == 0:
            return 1.0
        return round(self.success_count / self.tasks_completed, 2)

    @property
    def avg_time_sec(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return round(self.total_time_sec / self.tasks_completed, 2)

    def update(self, success: bool, test_passed: bool, review_passed: bool, duration_sec: float) -> None:
        """Update metrics dynamically after a task run."""
        self.tasks_completed += 1
        if success:
            self.success_count += 1
        if test_passed:
            self.test_pass_count += 1
        if review_passed:
            self.review_pass_count += 1

        self.total_time_sec += duration_sec

        # Dynamic Reliability Score calculation
        base_rate = self.success_rate
        test_rate = self.test_pass_count / self.tasks_completed if self.tasks_completed else 1.0
        review_rate = self.review_pass_count / self.tasks_completed if self.tasks_completed else 1.0

        self.reliability_score = round(0.5 * base_rate + 0.3 * test_rate + 0.2 * review_rate, 2)


@dataclass
class AIEmployee:
    """Represents an AI Employee registered in the AI Workforce."""

    employee_id: str
    name: str
    role: str
    department: str
    provider_name: str
    seniority: SeniorityLevel = SeniorityLevel.MID
    skills: List[str] = field(default_factory=list)
    cost_tier: str = "Free"  # Free, Local, Paid
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
