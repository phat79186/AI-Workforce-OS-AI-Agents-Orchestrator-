"""Engine registry — initialises and holds references to both systems.

Module-level dict so tools can access engines without server-state coupling.
Tests inject mocks by writing directly to ``_engines``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("mcp_server.engines")

_engines: dict[str, Any] = {
    "orchestrator": None,
    "orchestrator_error": None,
    "agentic_team": None,
    "agentic_team_error": None,
}


def init_engines() -> None:
    """Initialise both engines from their respective configs."""
    _init_orchestrator()
    _init_agentic_team()


def _init_orchestrator() -> None:
    try:
        from orchestrator.core.engine import Orchestrator

        orch = Orchestrator()
        _engines["orchestrator"] = orch
        _engines["orchestrator_error"] = None
        logger.info("Orchestrator initialised: %s", orch.get_available_agents())
    except Exception as exc:
        _engines["orchestrator"] = None
        _engines["orchestrator_error"] = str(exc)
        logger.error("Orchestrator init failed: %s", exc)


def _init_agentic_team() -> None:
    try:
        from agentic_team.engine import AgenticTeamEngine

        engine = AgenticTeamEngine()
        _engines["agentic_team"] = engine
        _engines["agentic_team_error"] = None
        logger.info("Agentic Team initialised: %s", engine.get_available_agents())
    except Exception as exc:
        _engines["agentic_team"] = None
        _engines["agentic_team_error"] = str(exc)
        logger.error("Agentic Team init failed: %s", exc)


def get_engine(name: str):
    """Retrieve an engine, raising ``ToolError`` if unavailable."""
    from fastmcp.exceptions import ToolError

    engine = _engines.get(name)
    if engine is None:
        err = _engines.get(f"{name}_error", "not initialised")
        raise ToolError(f"{name} is not available: {err}")
    return engine
