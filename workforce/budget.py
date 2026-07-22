"""Workforce Budget resource limits preventing over-recruitment and runaway agent loops."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WorkforceBudget:
    """Resource constraints for agent recruitment and execution."""

    max_total_agents: int = 10
    max_concurrent_agents: int = 4
    max_task_cost: float = 0.0
    max_retries: int = 3
    max_execution_time_sec: int = 1800

    def validate_recruitment(self, current_total_agents: int, current_concurrent_agents: int) -> bool:
        """Check if recruiting another agent exceeds budget limits."""
        if current_total_agents >= self.max_total_agents:
            return False
        if current_concurrent_agents >= self.max_concurrent_agents:
            return False
        return True
