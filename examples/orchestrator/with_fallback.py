#!/usr/bin/env python3
"""Demonstrates fallback behavior when a cloud agent fails.

The orchestrator automatically routes to a configured local fallback
when the primary agent encounters a transient error (connection, timeout, 5xx).

Usage:
    python examples/orchestrator/with_fallback.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from orchestrator.core import Orchestrator  # noqa: E402


def main():
    """Demonstrate fallback behavior on agent failure."""
    # Initialize — requires fallback config in agents.yaml:
    #   settings:
    #     fallback:
    #       enabled: true
    #       map:
    #         claude: local-instruct
    #         codex: local-code
    orch = Orchestrator()

    fallback_enabled = orch.fallback_manager.enabled
    fallback_map = orch.fallback_manager.fallback_map

    print(f"Fallback enabled: {fallback_enabled}")
    print(f"Fallback map: {fallback_map}")
    print(f"Offline mode: {orch.is_offline_mode}")
    print()

    if not fallback_enabled:
        print("Fallback is disabled. Enable it in agents.yaml:")
        print("  settings:")
        print("    fallback:")
        print("      enabled: true")
        print("      map:")
        print("        claude: local-instruct")
        return

    # Run the hybrid workflow — uses local for implementation, cloud for review
    # If the cloud agent is unreachable, it falls back to local
    result = orch.execute_task(
        task="Write a retry decorator with exponential backoff",
        workflow_name="hybrid",
        max_iterations=1,
    )

    print(f"Success: {result['success']}")
    for step in result["iterations"][0]["steps"]:
        agent = step["agent"]
        fallback_from = step.get("fallback_from")
        if fallback_from:
            print(f"  {agent} (fallback from {fallback_from}): {step['task']}")
        else:
            print(f"  {agent}: {step['task']}")


if __name__ == "__main__":
    main()
