"""Approval Manager for interactive human-in-the-loop user confirmation."""

from __future__ import annotations

import sys
from typing import Callable, Optional
from rich.prompt import Confirm


class ApprovalManager:
    """Manages user confirmation prompts for high-risk commands."""

    def __init__(self, prompt_fn: Optional[Callable[[str], bool]] = None) -> None:
        self._prompt_fn = prompt_fn

    def request_approval(self, action_description: str, rationale: str) -> bool:
        """Request explicit user approval for a dangerous operation."""
        if self._prompt_fn:
            return self._prompt_fn(action_description)

        # Default CLI prompt
        print(f"\n[HIGH-RISK ACTION REQUIRED] {action_description}")
        print(f"Rationale: {rationale}")
        try:
            return Confirm.ask("Do you approve this action?", default=False)
        except Exception:
            # Non-interactive fallback
            return False
