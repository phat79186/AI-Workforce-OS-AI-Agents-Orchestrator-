"""Ollama local LLM provider implementation."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from providers.base_provider import BaseProvider, ProviderMetadata, ProviderType


class OllamaProvider(BaseProvider):
    """Provider interface for local Ollama instances."""

    def __init__(
        self,
        model_name: str = "qwen2.5-coder:7b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        metadata = ProviderMetadata(
            name=f"ollama-{model_name}",
            provider_type=ProviderType.LOCAL,
            cost_per_1k_tokens=0.0,
            is_local=True,
            capabilities=["coding", "debugging", "testing", "research", "chat"],
            context_limit=32768,
            priority=10,  # Highest priority
            requires_approval=False,
        )
        super().__init__(metadata)
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def check_availability(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self.metadata.is_available = any(self.model_name in m for m in models) or True
                    return True
        except Exception:
            pass
        self.metadata.is_available = False
        return False

    def execute_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a prompt against Ollama /api/generate."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {
                    "response": res.get("response", ""),
                    "status": "success",
                    "model": self.model_name,
                    "tokens_used": res.get("eval_count", 0),
                    "provider": self.metadata.name,
                }
        except urllib.error.URLError as e:
            return {
                "response": "",
                "status": "error",
                "error": f"Ollama connection error: {e}",
                "provider": self.metadata.name,
            }
