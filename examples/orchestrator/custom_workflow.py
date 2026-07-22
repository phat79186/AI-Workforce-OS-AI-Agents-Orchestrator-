#!/usr/bin/env python3
"""Run a task with a specific workflow and custom iterations.

Demonstrates: workflow selection, iteration control, result inspection.

Usage:
    python examples/orchestrator/custom_workflow.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from orchestrator.core import Orchestrator  # noqa: E402


def main():
    """Demonstrate custom workflow usage."""
    orch = Orchestrator()

    # Use the "quick" workflow (codex only — fast, single agent)
    print("=== Quick Workflow (single agent) ===")
    result = orch.execute_task(
        task="Write a Python class for a stack data structure with push, pop, peek",
        workflow_name="quick",
        max_iterations=1,
    )
    print(f"Success: {result['success']}")
    print(f"Steps: {len(result['iterations'][0]['steps'])}")
    print()

    # Use the "review-only" workflow (gemini → claude)
    print("=== Review-Only Workflow ===")
    result = orch.execute_task(
        task="Review this code for security issues and suggest improvements",
        workflow_name="review-only",
        max_iterations=1,
    )
    print(f"Success: {result['success']}")
    for step in result["iterations"][0]["steps"]:
        print(f"  {step['agent']} ({step['task']}): {'OK' if step['success'] else 'FAIL'}")
    print()

    # Use the "thorough" workflow with multiple iterations
    print("=== Thorough Workflow (multi-iteration) ===")
    result = orch.execute_task(
        task="Build a complete binary search tree with insert, delete, search, and traversal",
        workflow_name="thorough",
        max_iterations=3,
    )
    print(f"Success: {result['success']}")
    print(f"Iterations used: {len(result['iterations'])}")
    for i, iteration in enumerate(result["iterations"]):
        agents = [s["agent"] for s in iteration["steps"]]
        print(f"  Iteration {i+1}: {' → '.join(agents)}")


if __name__ == "__main__":
    main()
