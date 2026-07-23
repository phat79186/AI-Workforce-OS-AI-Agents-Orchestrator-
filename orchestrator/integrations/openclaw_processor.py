"""Integration for openclaw/openclaw raw prompt pre-processor and code refinement engine."""

from __future__ import annotations

from typing import Any, Dict, Optional
from providers.openclaw_provider import OpenClawProvider


class OpenClawPromptProcessor:
    """Processor wrapping OpenClaw engine to transform raw user input into detailed technical specifications for downstream AI agents."""

    def __init__(self) -> None:
        self.provider = OpenClawProvider()

    def process_raw_input(
        self, raw_input: str, project_root: Optional[str] = None, domain_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pre-process raw input into structured technical specifications using Aegis V5.5 Context Scan."""
        return self.provider.refine_raw_prompt(raw_input, project_root=project_root, domain_context=domain_context)
