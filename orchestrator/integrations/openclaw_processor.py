"""Processor named after openclaw/openclaw, wrapping `providers.OpenClawProvider`.

⚠️ PARTIALLY SIMULATED: `scan_project_context()` genuinely reads real files
from disk (package.json, tailwind config, etc.) — that part is real. But the
actual "refinement" is keyword-branching over a handful of hardcoded
templates (see `providers/prompt_optimizer.py`), not an LLM call or the real
openclaw/openclaw or linshenkx/prompt-optimizer projects. Treat
`refine_raw_prompt()`'s output as a structured template, not an AI-generated
specification.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from providers.openclaw_provider import OpenClawProvider
from orchestrator.integrations._simulated import warn_simulated


class OpenClawPromptProcessor:
    """PARTIALLY SIMULATED processor — real file scan, but template-based (not LLM) refinement."""

    def __init__(self) -> None:
        warn_simulated("OpenClawPromptProcessor.refine_raw_prompt (templated, not LLM)", "openclaw/openclaw")
        self.provider = OpenClawProvider()

    def process_raw_input(
        self, raw_input: str, project_root: Optional[str] = None, domain_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pre-process raw input into structured technical specifications using Aegis V5.5 Context Scan."""
        return self.provider.refine_raw_prompt(raw_input, project_root=project_root, domain_context=domain_context)
