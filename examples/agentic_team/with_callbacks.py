#!/usr/bin/env python3
"""Agentic team with turn callbacks for real-time monitoring.

The turn_callback fires after each turn, giving you live visibility
into the team's communication as it happens.

Usage:
    python examples/agentic_team/with_callbacks.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agentic_team import AgenticTeamEngine  # noqa: E402


def on_turn(step: dict):
    """Called after each team turn to monitor progress."""
    turn = step["turn"]
    from_role = step["from_role"]
    to_role = step["to_role"]
    action = step["action"]
    agent = step["agent"]
    success = step["success"]
    message = step.get("message", "")[:80]

    icon = {
        "message": "-->",
        "finalize": ">>>",
    }.get(action, "???")

    status = "OK" if success else "FAIL"
    print(f"  [{status}] Turn {turn}: {from_role} ({agent}) {icon} {to_role}")
    print(f"           {message}")
    print()


def main():
    """Demonstrate team execution with turn callbacks."""
    engine = AgenticTeamEngine()

    validation = engine.validate_team_bindings()
    if not validation["valid"]:
        print(f"Team not valid: {validation}")
        return

    print("=== Agentic Team Execution (with live callbacks) ===")
    print()

    result = engine.execute_task(
        task="Build a CLI tool that converts CSV files to JSON with column filtering",
        max_turns=8,
        turn_callback=on_turn,
    )

    print("=" * 50)
    print(f"Result: {'SUCCESS' if result['success'] else 'INCOMPLETE'}")
    print(f"Reason: {result['termination_reason']}")
    print(f"Turns:  {result['stats']['turns_executed']}")
    if result["stats"]["fallback_count"] > 0:
        print(f"Fallbacks: {result['stats']['fallback_count']}")
    if result["stats"]["lead_escalation_count"] > 0:
        print(f"Escalations: {result['stats']['lead_escalation_count']}")


if __name__ == "__main__":
    main()
