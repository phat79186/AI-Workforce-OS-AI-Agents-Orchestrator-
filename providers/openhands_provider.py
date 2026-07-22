"""OpenHands open-source coding agent provider implementation."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, Optional

from providers.base_provider import BaseProvider, ProviderMetadata, ProviderType


class OpenHandsProvider(BaseProvider):
    """Provider interface for OpenHands CLI/Agent execution."""

    def __init__(
        self,
        llm_model: str = "ollama/qwen2.5-coder:7b",
        llm_base_url: str = "http://localhost:11434",
        runtime: str = "local",
    ) -> None:
        metadata = ProviderMetadata(
            name="openhands",
            provider_type=ProviderType.OPEN_SOURCE,
            cost_per_1k_tokens=0.0,
            is_local=True,
            capabilities=["coding", "debugging", "repository_refactor", "testing"],
            context_limit=65536,
            priority=20,  # Second highest priority (Level 2)
            requires_approval=False,
        )
        super().__init__(metadata)
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.runtime = runtime

    def check_availability(self) -> bool:
        """Check if OpenHands CLI or python module is available in PATH."""
        is_installed = (
            shutil.which("openhands") is not None
            or shutil.which("openhands-cli") is not None
        )
        self.metadata.is_available = is_installed
        return is_installed

    def execute_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a task prompt using OpenHands CLI in headless mode."""
        cmd = ["openhands", "exec", prompt]
        env = os.environ.copy()
        env["LLM_MODEL"] = self.llm_model
        env["LLM_BASE_URL"] = self.llm_base_url
        env["LLM_API_KEY"] = env.get("LLM_API_KEY", "ollama")
        env["OPENHANDS_RUNTIME"] = self.runtime

        cwd = kwargs.get("working_dir", os.getcwd())

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=kwargs.get("timeout", 600),
                cwd=cwd,
                env=env,
            )
            return {
                "response": res.stdout,
                "stderr": res.stderr,
                "status": "success" if res.returncode == 0 else "failed",
                "exit_code": res.returncode,
                "provider": self.metadata.name,
            }
        except Exception as e:
            return {
                "response": "",
                "status": "error",
                "error": f"OpenHands execution error: {e}",
                "provider": self.metadata.name,
            }
