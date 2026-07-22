#!/usr/bin/env python3
"""Basic agentic team usage — run a task with role-based collaboration.

The team routes messages between roles (PM, Architect, Developer, QA, DevOps)
until the lead role (Project Manager) finalizes and delivers the result.

Usage:
    python examples/agentic_team/basic_usage.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agentic_team import AgenticTeamEngine  # noqa: E402


def main():
    """Demonstrate basic agentic team usage."""
    # Initialize with default config
    engine = AgenticTeamEngine()

    print(f"Available agents: {engine.get_available_agents()}")
    team_config = engine.get_team_config()
    print(f"Lead role: {team_config['lead_role']}")
    print(f"Roles: {list(team_config['roles'].keys())}")
    print(f"Max turns: {team_config['max_turns']}")
    print()

    # Validate team bindings
    validation = engine.validate_team_bindings()
    print(f"Team valid: {validation['valid']}")
    if validation.get("missing_roles"):
        print(f"Missing: {validation['missing_roles']}")
        return
    print()

    # Execute a task — the team collaborates autonomously
    print("=== Executing Task ===")
    result = engine.execute_task(
        task="Design and implement a rate limiter with token bucket algorithm",
        max_turns=12,
    )

    print(f"\nSuccess: {result['success']}")
    print(f"Termination: {result['termination_reason']}")
    print(f"Turns: {result['stats']['turns_executed']}")
    print(f"Duration: {result['duration_ms']}ms")
    print()

    # Print the communication flow
    print("=== Team Communication ===")
    for step in result["iterations"][0]["steps"]:
        action = step["action"]
        icon = ">>>" if action == "finalize" else "-->"
        print(f"  Turn {step['turn']}: {step['from_role']} {icon} {step['to_role']} [{action}]")
    print()

    # Final output
    print("=== Final Output ===")
    print(result.get("final_output", "(none)")[:500])


if __name__ == "__main__":
    main()
