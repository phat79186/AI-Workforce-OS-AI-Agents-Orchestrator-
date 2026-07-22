"""Schema for structured clarification requests.

When an agent genuinely cannot proceed without user input, it returns
a structured clarification request instead of asking the user directly
in prose. The orchestrator/team engine catches this and surfaces it
through the proper channel (UI, CLI, or MCP).

Expected JSON from agent:
{
    "clarification_needed": true,
    "questions": ["What database should I use?", "REST or GraphQL?"],
    "context": "I need to decide the API style before implementing",
    "partial_work": "Here's what I have so far..."
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClarificationRequest:
    """Structured clarification request from an agent."""

    questions: list[str] = field(default_factory=list)
    context: str = ""
    partial_work: str = ""
    asking_role: str = ""
    asking_agent: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert clarification request to dictionary format."""
        return {
            "clarification_needed": True,
            "questions": self.questions,
            "context": self.context,
            "partial_work": self.partial_work[:2000],
            "asking_role": self.asking_role,
            "asking_agent": self.asking_agent,
        }


def detect_clarification_request(output: str) -> ClarificationRequest | None:
    """Detect if agent output contains a structured clarification request.

    Returns ClarificationRequest if found, None otherwise.
    """
    if not output or "clarification_needed" not in output.lower():
        return None

    # Try to parse as JSON
    try:
        data = json.loads(output)
        if isinstance(data, dict) and data.get("clarification_needed"):
            return ClarificationRequest(
                questions=data.get("questions", []),
                context=data.get("context", ""),
                partial_work=data.get("partial_work", ""),
            )
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find embedded JSON
    import re

    for match in re.finditer(r"\{[^}]*clarification_needed[^}]*\}", output, re.DOTALL):
        try:
            data = json.loads(match.group())
            if data.get("clarification_needed"):
                return ClarificationRequest(
                    questions=data.get("questions", []),
                    context=data.get("context", ""),
                    partial_work=data.get("partial_work", ""),
                )
        except (json.JSONDecodeError, TypeError):
            continue

    return None


def build_clarification_response_prompt(
    original_task: str,
    questions: list[str],
    user_answers: list[str],
    partial_work: str = "",
) -> str:
    """Build a prompt that includes the user's answers to clarification questions.

    This is sent back to the agent after the user responds.
    """
    qa_pairs = []
    for i, (q, a) in enumerate(zip(questions, user_answers), 1):
        qa_pairs.append(f"Q{i}: {q}\nA{i}: {a}")

    parts = [
        f"## Original Task\n{original_task}",
        "",
        "## Clarification Answers",
        "You previously asked for clarification. The user has responded:",
        "",
        "\n\n".join(qa_pairs),
        "",
    ]

    if partial_work:
        parts.extend(
            [
                "## Your Previous Partial Work",
                partial_work[:4000],
                "",
            ]
        )

    parts.append(
        "Now proceed with the task using the clarification provided. "
        "Do NOT ask for further clarification — implement based on the answers above."
    )

    return "\n".join(parts)
