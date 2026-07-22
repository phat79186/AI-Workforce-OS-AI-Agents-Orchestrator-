"""Fallback execution manager for agent failures."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from orchestrator.adapters import AgentResponse, BaseAdapter


class FallbackManager:
    """Manage cloud-to-local fallback routing."""

    def __init__(self, config: dict[str, Any], logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("orchestrator.fallback")
        self.enabled, self.fallback_map = self._parse_fallback_config(config)

    def _parse_fallback_config(self, config: dict[str, Any]) -> tuple[bool, dict[str, str]]:
        settings = config.get("settings", {})
        fallback_config = settings.get("fallback", {})

        if not isinstance(fallback_config, dict):
            return False, {}

        enabled = bool(fallback_config.get("enabled", False))
        mapping: dict[str, str] = {}

        raw_map = fallback_config.get("map", {})
        if isinstance(raw_map, dict):
            mapping.update({str(k): str(v) for k, v in raw_map.items()})

        for key, value in fallback_config.items():
            if key in {"enabled", "map"}:
                continue
            if isinstance(value, str):
                mapping[str(key)] = value

        return enabled, mapping

    def resolve_fallback(
        self, primary_agent: str, explicit_fallback: str | None = None
    ) -> str | None:
        """Resolve fallback agent from explicit setting or configured map."""
        if explicit_fallback:
            return explicit_fallback
        return self.fallback_map.get(primary_agent)

    def should_fallback(self, error: str | None = None, exception: Exception | None = None) -> bool:
        """Determine whether failure resembles transient network/API outage."""
        if not self.enabled:
            return False

        if exception is not None:
            if isinstance(exception, (ConnectionError, TimeoutError, OSError, httpx.RequestError)):
                return True
            if isinstance(exception, httpx.HTTPStatusError):
                return exception.response.status_code >= 500

        if not error:
            return False

        message = error.lower()
        indicators = (
            "connection",
            "network",
            "timed out",
            "timeout",
            "temporary failure",
            "dns",
            "unreachable",
            "api error",
            "http error",
            "503",
            "502",
            "504",
        )
        return any(token in message for token in indicators)

    def execute_with_fallback(  # pylint: disable=too-many-return-statements
        self,
        *,
        primary_agent: str,
        adapters: dict[str, BaseAdapter],
        task: str,
        context: dict[str, Any],
        explicit_fallback: str | None = None,
    ) -> tuple[str, AgentResponse, str | None]:
        """Execute primary agent and fallback when applicable.

        Returns:
            tuple(agent_used, response, fallback_from_agent)
        """
        if primary_agent not in adapters:
            return (
                primary_agent,
                AgentResponse(
                    success=False,
                    output="",
                    error=f"Primary agent '{primary_agent}' not found in available adapters",
                ),
                None,
            )

        primary_adapter = adapters[primary_agent]
        fallback_agent = self.resolve_fallback(primary_agent, explicit_fallback)

        try:
            response = primary_adapter.execute_task(task, context)
        except Exception as exc:
            if not fallback_agent or fallback_agent not in adapters:
                return primary_agent, AgentResponse(success=False, output="", error=str(exc)), None
            if not self.should_fallback(exception=exc):
                return primary_agent, AgentResponse(success=False, output="", error=str(exc)), None

            self.logger.warning(
                "Primary agent '%s' failed (%s), falling back to '%s'",
                primary_agent,
                exc,
                fallback_agent,
            )
            try:
                fallback_response = adapters[fallback_agent].execute_task(task, context)
                return fallback_agent, fallback_response, primary_agent
            except Exception as fallback_exc:
                return (
                    primary_agent,
                    AgentResponse(
                        success=False,
                        output="",
                        error=(
                            f"Primary failed: {exc}; "
                            f"fallback '{fallback_agent}' failed: {fallback_exc}"
                        ),
                    ),
                    None,
                )

        if response.success:
            return primary_agent, response, None

        if not fallback_agent or fallback_agent not in adapters:
            return primary_agent, response, None
        if not self.should_fallback(error=response.error):
            return primary_agent, response, None

        self.logger.warning(
            "Primary agent '%s' returned recoverable error (%s), falling back to '%s'",
            primary_agent,
            response.error,
            fallback_agent,
        )
        try:
            fallback_response = adapters[fallback_agent].execute_task(task, context)
            return fallback_agent, fallback_response, primary_agent
        except Exception as fallback_exc:
            return (
                primary_agent,
                AgentResponse(
                    success=False,
                    output="",
                    error=(
                        f"Primary failed: {response.error}; "
                        f"fallback '{fallback_agent}' failed: {fallback_exc}"
                    ),
                ),
                None,
            )
