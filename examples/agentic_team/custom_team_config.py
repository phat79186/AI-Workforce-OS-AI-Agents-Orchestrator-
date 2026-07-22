#!/usr/bin/env python3
"""Configure the agentic team with custom role-to-agent mappings.

Shows how to inspect and override team configuration programmatically.

Usage:
    python examples/agentic_team/custom_team_config.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agentic_team import AgenticTeamEngine  # noqa: E402
from agentic_team.config_utils import normalize_role, validate_team_bindings  # noqa: E402


def main():
    """Demonstrate custom team configuration."""
    engine = AgenticTeamEngine()

    # --- Inspect current config ---
    print("=== Current Team Configuration ===")
    team_config = engine.get_team_config()

    for role_name, spec in team_config["roles"].items():
        title = spec.get("title", role_name)
        agent = spec.get("agent", "?")
        resp = spec.get("responsibilities", "")[:60]
        print(f"  {title}")
        print(f"    Agent: {agent}")
        print(f"    Duties: {resp}")
        print()

    # --- Validate bindings ---
    print("=== Validation ===")
    validation = validate_team_bindings(team_config, engine.get_available_agents())
    print(f"  Valid: {validation['valid']}")
    print(f"  Available agents: {validation['available_agents']}")
    if validation["missing_roles"]:
        print(f"  Missing: {validation['missing_roles']}")
    print()

    # --- Role normalization ---
    print("=== Role Normalization ===")
    examples = [
        "Project Manager",
        "software-developer",
        "QA  Engineer",
        "dev--ops",
        "  lead  ",
    ]
    for raw in examples:
        print(f"  '{raw}' → '{normalize_role(raw)}'")
    print()

    # --- Runtime status ---
    print("=== Runtime Status ===")
    status = engine.get_runtime_status()
    print(f"  Engine: {status['engine']}")
    print(f"  Config: {status['config_path']}")
    print(f"  Offline: {status['offline_mode']}")
    print(f"  Agents: {status['available_agents']}")
    print(f"  Settings: {status['runtime_settings']}")


if __name__ == "__main__":
    main()
