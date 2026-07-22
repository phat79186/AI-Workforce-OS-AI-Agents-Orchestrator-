"""Metrics Analyzer evaluating historical task outcomes for Phase 7 Self-Improvement."""

from __future__ import annotations

from typing import Any, Dict, List


class MetricsAnalyzer:
    """Analyzes task history metrics to optimize routing strategies dynamically."""

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def record_outcome(self, agent_role: str, provider_name: str, task_type: str, success: bool) -> None:
        """Record task execution outcome."""
        self.history.append({
            "agent_role": agent_role,
            "provider_name": provider_name,
            "task_type": task_type,
            "success": success,
        })

    def calculate_success_rates(self) -> Dict[str, float]:
        """Calculate success rates per (Agent, Provider) pair."""
        totals: Dict[str, int] = {}
        successes: Dict[str, int] = {}

        for entry in self.history:
            key = f"{entry['agent_role']}::{entry['provider_name']}"
            totals[key] = totals.get(key, 0) + 1
            if entry["success"]:
                successes[key] = successes.get(key, 0) + 1

        rates = {}
        for key, total in totals.items():
            rates[key] = round(successes.get(key, 0) / total, 2)
        return rates
