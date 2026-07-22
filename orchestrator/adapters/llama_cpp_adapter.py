"""Adapter for llama.cpp/OpenAI-compatible local model servers."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .base import AgentCapability, AgentResponse, BaseAdapter


class LlamaCppAdapter(BaseAdapter):
    """Adapter for local OpenAI-compatible completion endpoints."""

    def __init__(self, config: dict[str, Any]):
        local_config = dict(config)
        local_config.setdefault("offline", True)
        super().__init__(local_config)
        self.endpoint = str(local_config.get("endpoint", "http://localhost:8080")).rstrip("/")
        self.model = local_config.get("model")
        self.model_path = local_config.get("model_path")
        try:
            self.max_tokens = max(1, int(local_config.get("max_tokens", 4096)))
        except (TypeError, ValueError):
            self.max_tokens = 4096
        try:
            self.temperature = max(0.0, min(2.0, float(local_config.get("temperature", 0.7))))
        except (TypeError, ValueError):
            self.temperature = 0.7
        try:
            self.timeout = max(1, int(local_config.get("timeout", 3600)))
        except (TypeError, ValueError):
            self.timeout = 3600

    def get_capabilities(self) -> list[AgentCapability]:
        """Return supported coding and review capabilities."""
        return [
            AgentCapability.IMPLEMENTATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
        ]

    def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
        """Execute task synchronously, delegating to async transport when possible."""
        try:
            asyncio.get_running_loop()
            return self._execute_task_sync(task, context)
        except RuntimeError:
            return asyncio.run(self.execute_task_async(task, context))

    def _build_payload(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": self._build_local_llm_prompt(task, context),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stop": ["```\n\n", "Human:", "User:"],
        }
        if self.model:
            payload["model"] = self.model
        return payload

    def _parse_text_response(self, data: dict[str, Any]) -> str:
        if not isinstance(data, dict):
            return ""
        choices = data.get("choices", [])
        if not choices or not isinstance(choices, list):
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return str(first) if first else ""
        return str(first.get("text", ""))

    def _execute_task_sync(self, task: str, context: dict[str, Any]) -> AgentResponse:
        payload = self._build_payload(task, context)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.endpoint}/v1/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return AgentResponse(
                    success=True,
                    output=self._parse_text_response(data),
                    metadata={"model": self.model or "default"},
                )
        except httpx.HTTPStatusError as exc:
            return AgentResponse(success=False, output="", error=f"HTTP error: {exc}")
        except httpx.RequestError as exc:
            return AgentResponse(success=False, output="", error=f"Connection error: {exc}")
        except Exception as exc:
            return AgentResponse(success=False, output="", error=str(exc))

    async def execute_task_async(self, task: str, context: dict[str, Any]) -> AgentResponse:
        """Execute task via OpenAI-compatible async completion endpoint."""
        payload = self._build_payload(task, context)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.endpoint}/v1/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return AgentResponse(
                    success=True,
                    output=self._parse_text_response(data),
                    metadata={"model": self.model or "default"},
                )
        except httpx.HTTPStatusError as exc:
            return AgentResponse(success=False, output="", error=f"HTTP error: {exc}")
        except httpx.RequestError as exc:
            return AgentResponse(success=False, output="", error=f"Connection error: {exc}")
        except Exception as exc:
            return AgentResponse(success=False, output="", error=str(exc))

    def health_check(self) -> bool:
        """Check whether the endpoint responds as an OpenAI-compatible server."""
        checks = [
            (f"{self.endpoint}/health", {200}),
            (f"{self.endpoint}/v1/models", {200}),
            (self.endpoint, {200, 301, 302, 404}),
        ]
        for url, ok_codes in checks:
            try:
                resp = httpx.get(url, timeout=2, follow_redirects=False)
                if resp.status_code in ok_codes:
                    return True
            except Exception:  # nosec B112 - health probe; failure means offline
                continue
        return False

    def is_available(self) -> bool:
        """Return availability based on endpoint health probes."""
        return self.health_check()

    def list_models(self) -> list[str]:
        """List models from `/v1/models` when available."""
        try:
            resp = httpx.get(f"{self.endpoint}/v1/models", timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [str(item.get("id", "")) for item in data if item.get("id")]
        except Exception:
            return []
