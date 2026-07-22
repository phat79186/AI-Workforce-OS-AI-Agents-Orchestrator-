#!/usr/bin/env python3
"""Basic orchestrator usage — run a task through a workflow.

Usage:
    python examples/orchestrator/basic_usage.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from orchestrator.core import Orchestrator  # noqa: E402


def main():
    """Demonstrate basic orchestrator usage."""
    # Initialize with default config
    orch = Orchestrator()

    print(f"Available agents: {orch.get_available_agents()}")
    print(f"Available workflows: {orch.get_workflows()}")
    print()

    # Execute a task using the default workflow (codex → gemini → claude)
    result = orch.execute_task(
        task="Write a Python function that checks if a string is a palindrome",
        workflow_name="default",
        max_iterations=2,
    )

    print(f"Success: {result['success']}")
    print(f"Workflow: {result['workflow']}")
    print(f"Iterations: {len(result['iterations'])}")
    print()

    # Print each step's result
    for i, iteration in enumerate(result["iterations"]):
        print(f"--- Iteration {i + 1} ---")
        for step in iteration["steps"]:
            status = "OK" if step["success"] else "FAIL"
            print(f"  [{status}] {step['agent']} ({step['task']})")
            if step.get("suggestions"):
                print(f"       Suggestions: {len(step['suggestions'])}")
            if step.get("files_modified"):
                print(f"       Files: {step['files_modified']}")
        print()

    # Final output
    print("=== Final Output ===")
    print(result.get("final_output", "(none)")[:500])


if __name__ == "__main__":
    main()
