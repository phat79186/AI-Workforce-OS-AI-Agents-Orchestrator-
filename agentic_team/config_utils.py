"""Config normalization and validation helpers for Agentic Team."""

from __future__ import annotations

from typing import Any, Callable

from .constants import (
    DEFAULT_TEAM_MAX_TURNS,
    ROLE_DEVOPS_ENGINEER,
    ROLE_PROJECT_MANAGER,
    ROLE_QA_ENGINEER,
    ROLE_SOFTWARE_ARCHITECT,
    ROLE_SOFTWARE_DEVELOPER,
)


def normalize_role(role: str) -> str:
    """Normalize a role name into canonical snake_case form."""
    import re

    raw = str(role or "").strip().lower().replace("-", "_").replace(" ", "_")
    # Collapse consecutive underscores
    return re.sub(r"_+", "_", raw).strip("_")


def _coerce_positive_int(raw: Any, fallback: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return max(1, value)


def default_roles(
    pick_preferred_agent: Callable[[list[str]], str | None],
) -> dict[str, dict[str, Any]]:
    """Build default role specs with best-effort preferred agent picks."""
    return {
        ROLE_PROJECT_MANAGER: {
            "title": "Project Manager (Team Lead)",
            "agent": pick_preferred_agent(["claude", "gemini", "codex", "copilot"]),
            "responsibilities": "Initiate work, route subtasks, and perform final approval.",
        },
        ROLE_SOFTWARE_ARCHITECT: {
            "title": "Software Architect",
            "agent": pick_preferred_agent(["gemini", "claude", "codex", "copilot"]),
            "responsibilities": "Define architecture and technical design.",
        },
        ROLE_SOFTWARE_DEVELOPER: {
            "title": "Software Developer",
            "agent": pick_preferred_agent(["codex", "claude", "copilot", "gemini"]),
            "responsibilities": "Implement and update source code.",
        },
        ROLE_QA_ENGINEER: {
            "title": "QA Engineer",
            "agent": pick_preferred_agent(["gemini", "copilot", "claude", "codex"]),
            "responsibilities": "Validate behavior and identify regressions.",
        },
        ROLE_DEVOPS_ENGINEER: {
            "title": "DevOps Engineer",
            "agent": pick_preferred_agent(["claude", "codex", "gemini", "copilot"]),
            "responsibilities": "Handle deployment, runtime, and operational concerns.",
        },
    }


def resolve_team_config(
    root_config: dict[str, Any],
    pick_preferred_agent: Callable[[list[str]], str | None],
) -> dict[str, Any]:
    """Resolve effective team config by merging defaults + agentic_team overrides."""
    raw = root_config.get("agentic_team", {})
    roles = default_roles(pick_preferred_agent)

    if isinstance(raw, dict):
        configured_roles = raw.get("roles", {})
        if isinstance(configured_roles, dict):
            for raw_role, raw_spec in configured_roles.items():
                role_name = normalize_role(str(raw_role))
                if not role_name:
                    continue
                if isinstance(raw_spec, str):
                    spec = {"agent": raw_spec}
                elif isinstance(raw_spec, dict):
                    spec = dict(raw_spec)
                else:
                    continue
                merged = dict(roles.get(role_name, {}))
                merged.update(spec)
                merged.setdefault("title", role_name.replace("_", " ").title())
                if not merged.get("agent"):
                    fallback_agent = pick_preferred_agent([])
                    if fallback_agent:
                        merged["agent"] = fallback_agent
                    # Even if None, we still store the role; validation catches it later
                roles[role_name] = merged

    lead_role = normalize_role(
        str(raw.get("lead_role", ROLE_PROJECT_MANAGER))
        if isinstance(raw, dict)
        else ROLE_PROJECT_MANAGER
    )
    max_turns = _coerce_positive_int(
        (
            raw.get("max_turns", DEFAULT_TEAM_MAX_TURNS)
            if isinstance(raw, dict)
            else DEFAULT_TEAM_MAX_TURNS
        ),
        DEFAULT_TEAM_MAX_TURNS,
    )

    return {"lead_role": lead_role, "max_turns": max_turns, "roles": roles}


def validate_team_bindings(team_cfg: dict[str, Any], available_agents: list[str]) -> dict[str, Any]:
    """Return validation payload for role->agent assignments."""
    roles = team_cfg.get("roles", {}) if isinstance(team_cfg, dict) else {}
    lead_role = team_cfg.get("lead_role", "") if isinstance(team_cfg, dict) else ""
    available = sorted(str(name) for name in (available_agents or []))
    available_set = set(available)

    missing_roles = []
    if not roles:
        return {
            "valid": False,
            "available_agents": available,
            "missing_roles": [],
            "reason": "no_roles_configured",
            "error": "Agentic team has no roles configured",
        }

    if lead_role not in roles:
        return {
            "valid": False,
            "available_agents": available,
            "missing_roles": [],
            "reason": "invalid_lead_role",
            "error": f"Lead role '{lead_role}' is not configured",
        }

    for role_name, role_spec in roles.items():
        spec = role_spec if isinstance(role_spec, dict) else {}
        agent_name = spec.get("agent")
        if not isinstance(agent_name, str) or not agent_name or agent_name not in available_set:
            missing_roles.append({"role": str(role_name), "agent": agent_name})

    reason = ""
    if not available:
        reason = "no_available_agents"
    elif missing_roles:
        reason = "invalid_mappings"

    return {
        "valid": len(missing_roles) == 0 and bool(available),
        "available_agents": available,
        "missing_roles": missing_roles,
        "reason": reason,
    }
