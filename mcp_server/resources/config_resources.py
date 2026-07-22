"""MCP resources serving live YAML configurations."""

from __future__ import annotations

from pathlib import Path


def register(mcp):
    """Register config resources."""
    project_root = Path(__file__).resolve().parent.parent.parent

    @mcp.resource("config://orchestrator")
    def orchestrator_config_resource() -> str:
        """Current orchestrator YAML configuration."""
        cfg = project_root / "orchestrator" / "config" / "agents.yaml"
        return cfg.read_text(encoding="utf-8") if cfg.exists() else "# Config not found"

    @mcp.resource("config://agentic-team")
    def agentic_team_config_resource() -> str:
        """Current agentic team YAML configuration."""
        cfg = project_root / "agentic_team" / "config" / "agents.yaml"
        return cfg.read_text(encoding="utf-8") if cfg.exists() else "# Config not found"
