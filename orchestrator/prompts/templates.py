"""Prompt template rendering for orchestrator workflow steps.

Assembles the final prompt from: system prompt + task + context + constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .system_prompts import get_error_recovery_prompt, get_system_prompt


@dataclass
class PromptTemplate:
    """Configurable prompt template for a workflow step."""

    role: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    max_context_chars: int = 8000

    def render(self) -> str:
        """Render the full prompt."""
        parts: list[str] = []

        # System prompt (role-specific)
        parts.append(get_system_prompt(self.role))
        parts.append("")

        # Task
        parts.append(f"## Task\n{self.task}")
        parts.append("")

        # Previous output context
        if self.context.get("previous_output"):
            prev = str(self.context["previous_output"])
            if len(prev) > self.max_context_chars:
                prev = prev[: self.max_context_chars] + "\n\n[... truncated ...]"
            parts.append(f"## Previous Step Output\n{prev}")
            parts.append("")

        # Feedback from review
        if self.context.get("feedback"):
            parts.append(f"## Review Feedback\n{self.context['feedback']}")
            parts.append("")

        # Implementation to review/refine
        if self.context.get("implementation"):
            impl = str(self.context["implementation"])
            if len(impl) > self.max_context_chars:
                impl = impl[: self.max_context_chars] + "\n\n[... truncated ...]"
            parts.append(f"## Current Implementation\n{impl}")
            parts.append("")

        # Files
        if self.context.get("files"):
            files_str = ", ".join(self.context["files"][:20])
            parts.append(f"## Relevant Files\n{files_str}")
            parts.append("")

        # Error recovery
        if self.context.get("previous_error"):
            parts.append(
                get_error_recovery_prompt(
                    error=self.context["previous_error"],
                    previous_output=self.context.get("previous_output", ""),
                )
            )
            parts.append("")

        # Iteration context
        iteration = self.context.get("iteration", 0)
        max_iter = self.context.get("max_iterations", 3)
        if iteration > 0:
            parts.append(
                f"## Iteration\nThis is iteration {iteration + 1}/{max_iter}. "
                f"Build on the work from previous iterations."
            )

        return "\n".join(parts)


def render_prompt(role: str, task: str, context: dict[str, Any] | None = None) -> str:
    """Convenience function to render a prompt.

    Args:
        role: Workflow role (implement, review, refine, test, document)
        task: The task description
        context: Optional context dict with previous_output, feedback, etc.

    Returns:
        Rendered prompt string
    """
    return PromptTemplate(role=role, task=task, context=context or {}).render()
