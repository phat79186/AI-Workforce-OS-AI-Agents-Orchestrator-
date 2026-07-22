#!/usr/bin/env python3
"""Use individual adapters directly without the workflow engine.

Useful when you need fine-grained control over which agent does what.

Usage:
    python examples/orchestrator/programmatic_adapters.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from orchestrator.adapters import ClaudeAdapter, CodexAdapter, GeminiAdapter  # noqa: E402


def main():
    """Demonstrate direct adapter usage."""
    # Initialize individual adapters
    codex = CodexAdapter({"name": "codex", "command": "codex", "enabled": True, "timeout": 60})
    gemini = GeminiAdapter({"name": "gemini", "command": "gemini", "enabled": True, "timeout": 60})
    claude = ClaudeAdapter({"name": "claude", "command": "claude", "enabled": True, "timeout": 60})

    # Check availability
    for adapter in [codex, gemini, claude]:
        status = "available" if adapter.is_available() else "not found"
        caps = [c.value for c in adapter.get_capabilities()]
        print(f"  {adapter.name}: {status} — capabilities: {caps}")
    print()

    # Use codex for implementation
    if codex.is_available():
        print("=== Step 1: Codex implements ===")
        result = codex.execute_task(
            "Write a Python function to merge two sorted lists",
            {"working_dir": ".", "role": "implement"},
        )
        print(f"  Success: {result.success}")
        if result.output:
            print(f"  Output: {result.output[:200]}...")
        print()

        # Use gemini to review
        if gemini.is_available():
            print("=== Step 2: Gemini reviews ===")
            review = gemini.execute_task(
                "Review this merge function for correctness and edge cases",
                {"working_dir": ".", "role": "review", "implementation": result.output},
            )
            print(f"  Success: {review.success}")
            print(f"  Suggestions: {len(review.suggestions)}")
            for s in review.suggestions[:3]:
                print(f"    - {s[:80]}")
    else:
        print("Codex not available — install with: npm install -g @openai/codex")


if __name__ == "__main__":
    main()
