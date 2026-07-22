"""Adapter for Ollama local model server."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .base import AgentCapability, AgentResponse, BaseAdapter


class OllamaAdapter(BaseAdapter):
    """Adapter for interacting with Ollama local model server."""

    CAPABILITY_MAP = {
        "code": AgentCapability.IMPLEMENTATION,
        "review": AgentCapability.CODE_REVIEW,
        "docs": AgentCapability.DOCUMENTATION,
        "general": AgentCapability.DOCUMENTATION,
        "test": AgentCapability.TESTING,
        "refactor": AgentCapability.REFACTORING,
    }

    def __init__(self, config: dict[str, Any]):
        local_config = dict(config)
        local_config.setdefault("offline", True)
        super().__init__(local_config)
        self.model = local_config.get("model", "codellama:13b")
        self.endpoint = str(local_config.get("endpoint", "http://localhost:11434")).rstrip("/")
        self.timeout = int(local_config.get("timeout", 3600))
        self.keep_alive = local_config.get("keep_alive", "5m")

    def get_capabilities(self) -> list[AgentCapability]:
        """Return adapter capabilities, honoring config override when provided."""
        configured = self.config.get("capabilities")
        if isinstance(configured, list) and configured:
            mapped = [
                self.CAPABILITY_MAP.get(str(item).lower())
                for item in configured
                if self.CAPABILITY_MAP.get(str(item).lower())
            ]
            if mapped:
                return mapped

        return [
            AgentCapability.IMPLEMENTATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
        ]

    def execute_task(self, task: str, context: dict[str, Any]) -> AgentResponse:
        """Synchronous wrapper around async execution."""
        try:
            asyncio.get_running_loop()
            return self._execute_task_sync(task, context)
        except RuntimeError:
            return asyncio.run(self.execute_task_async(task, context))

    def _execute_task_sync(self, task: str, context: dict[str, Any]) -> AgentResponse:
        prompt = self._build_local_llm_prompt(task, context)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.endpoint}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return AgentResponse(
                    success=True,
                    output=str(data.get("response", "")),
                    metadata={
                        "model": self.model,
                        "eval_count": data.get("eval_count"),
                        "eval_duration": data.get("eval_duration"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                        "prompt_eval_duration": data.get("prompt_eval_duration"),
                    },
                )
        except httpx.HTTPStatusError as exc:
            return AgentResponse(success=False, output="", error=f"HTTP error: {exc}")
        except httpx.RequestError as exc:
            return AgentResponse(success=False, output="", error=f"Connection error: {exc}")
        except Exception as exc:
            return AgentResponse(success=False, output="", error=str(exc))

    async def execute_task_async(self, task: str, context: dict[str, Any]) -> AgentResponse:
        """Execute a task using Ollama's async API."""
        prompt = self._build_local_llm_prompt(task, context)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.endpoint}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return AgentResponse(
                    success=True,
                    output=str(data.get("response", "")),
                    metadata={
                        "model": self.model,
                        "eval_count": data.get("eval_count"),
                        "eval_duration": data.get("eval_duration"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                        "prompt_eval_duration": data.get("prompt_eval_duration"),
                    },
                )
        except httpx.HTTPStatusError as exc:
            return AgentResponse(success=False, output="", error=f"HTTP error: {exc}")
        except httpx.RequestError as exc:
            return AgentResponse(success=False, output="", error=f"Connection error: {exc}")
        except Exception as exc:
            return AgentResponse(success=False, output="", error=str(exc))

    def health_check(self) -> bool:
        """Check Ollama endpoint health."""
        try:
            response = httpx.get(f"{self.endpoint}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        """Return availability based on endpoint health."""
        return self.health_check()

    def list_models(self) -> list[str]:
        """Return available models on the Ollama server."""
        try:
            resp = httpx.get(f"{self.endpoint}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return [str(item.get("name", "")) for item in models if item.get("name")]
        except Exception as exc:
            self.logger.warning("Failed to list Ollama models from %s: %s", self.endpoint, exc)
            return []

    def pull_model(self, model: str | None = None) -> AgentResponse:
        """Pull a model into the local Ollama cache."""
        model_name = model or self.model
        try:
            response = httpx.post(
                f"{self.endpoint}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return AgentResponse(success=True, output=f"Pulled model '{model_name}'")
        except Exception as exc:
            return AgentResponse(success=False, output="", error=f"Failed to pull model: {exc}")

    def remove_model(self, model: str | None = None) -> AgentResponse:
        """Remove a model from the local Ollama cache."""
        model_name = model or self.model
        try:
            response = httpx.delete(  # pylint: disable=unexpected-keyword-arg
                f"{self.endpoint}/api/delete",
                json={"name": model_name},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return AgentResponse(success=True, output=f"Removed model '{model_name}'")
        except Exception as exc:
            return AgentResponse(success=False, output="", error=f"Failed to remove model: {exc}")
