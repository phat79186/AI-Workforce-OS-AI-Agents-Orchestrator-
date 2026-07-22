#!/usr/bin/env python3
"""Demonstrates the decision parser that extracts routing decisions from LLM output.

The parser handles multiple formats:
1. Direct JSON
2. JSON in fenced code blocks (```json ... ```)
3. JSON embedded in prose text
4. Key-value lines (action: message, to_role: dev)

Usage:
    python examples/agentic_team/decision_parsing.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agentic_team import DecisionParser  # noqa: E402


def main():
    """Demonstrate decision parsing from various formats."""
    parser = DecisionParser()

    examples = [
        # 1. Direct JSON
        (
            "Direct JSON",
            '{"action": "message", "to_role": "software_developer", "message": "Please implement the auth module"}',
        ),
        # 2. JSON in fenced block
        (
            "Fenced code block",
            'I think we should proceed with the implementation.\n\n```json\n{"action": "message", "to_role": "qa_engineer", "message": "Please test the auth module"}\n```\n\nLet me know if you have questions.',
        ),
        # 3. JSON embedded in prose
        (
            "JSON in prose",
            'After careful review, my decision is {"action": "finalize", "final_response": "Authentication module complete with JWT tokens and refresh flow", "message": "Delivering to user"} and that concludes the work.',
        ),
        # 4. Key-value lines
        (
            "Key-value lines",
            "action: message\nto_role: software_architect\nmessage: Please review the design before implementation",
        ),
        # 5. Plain text (no structured format)
        (
            "Plain text fallback",
            "I think we should implement this using a factory pattern with dependency injection.",
        ),
    ]

    for title, output in examples:
        print(f"=== {title} ===")
        print(f"  Input: {output[:80]}...")
        print()

        # Extract JSON
        json_obj = parser.extract_json_object(output)
        print(f"  Extracted JSON: {json_obj}")

        # Parse routing decision
        decision = parser.parse_decision(
            output=output,
            current_role="project_manager",
            lead_role="project_manager",
            default_to_role="software_developer",
        )
        print(f"  Decision:")
        print(f"    action:         {decision['action']}")
        print(f"    to_role:        {decision['to_role']}")
        print(f"    message:        {decision['message'][:60]}...")
        print(
            f"    final_response: {decision['final_response'][:60] if decision['final_response'] else '(none)'}"
        )
        print()

    # Demonstrate privilege check: non-lead trying to finalize
    print("=== Privilege Check ===")
    decision = parser.parse_decision(
        output='{"action": "finalize", "final_response": "Done!", "message": "bypass"}',
        current_role="software_developer",  # Not the lead!
        lead_role="project_manager",
        default_to_role="project_manager",
    )
    print(f"  Developer tried to finalize:")
    print(f"    action:  {decision['action']}  (downgraded from 'finalize')")
    print(f"    to_role: {decision['to_role']}  (redirected to lead)")


if __name__ == "__main__":
    main()
