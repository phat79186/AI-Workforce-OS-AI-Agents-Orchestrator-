"""Schemas for validating and parsing agent output in the orchestrator.

Agents may return structured or unstructured output. These schemas define
the expected structure and provide parsing/validation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentOutputType(Enum):
    """Classification of agent output."""

    CODE = "code"
    REVIEW = "review"
    ERROR = "error"
    CLARIFICATION = "clarification"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class ParsedAgentOutput:
    """Structured representation of agent output after parsing."""

    raw: str
    output_type: AgentOutputType = AgentOutputType.UNKNOWN
    code_blocks: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    files_mentioned: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_clarification(self) -> bool:
        """Check if output indicates clarification is needed."""
        return self.output_type == AgentOutputType.CLARIFICATION or bool(
            self.clarification_questions
        )

    @property
    def has_errors(self) -> bool:
        """Check if output contains errors."""
        return self.output_type == AgentOutputType.ERROR or bool(self.errors)


def classify_output(output: str) -> AgentOutputType:
    """Classify the type of agent output based on content analysis."""
    if not output or not output.strip():
        return AgentOutputType.ERROR

    lower = output.lower()

    # Check for error indicators
    error_signals = [
        "error:",
        "traceback",
        "exception:",
        "failed to",
        "cannot ",
        "unable to",
        "permission denied",
        "command not found",
        "syntax error",
    ]
    if any(sig in lower for sig in error_signals):
        return AgentOutputType.ERROR

    # Check for clarification requests
    clarification_signals = [
        "could you clarify",
        "i need more information",
        "can you specify",
        "which approach would you prefer",
        "before i proceed",
        "please clarify",
        "i have a question",
        "do you want me to",
        "should i ",
        "would you like",
        "what do you mean by",
    ]
    if any(sig in lower for sig in clarification_signals):
        return AgentOutputType.CLARIFICATION

    # Check for code blocks
    if "```" in output:
        return AgentOutputType.CODE

    # Check for review patterns
    review_signals = [
        "suggestion:",
        "recommendation:",
        "issue:",
        "critical:",
        "high:",
        "medium:",
        "low:",
        "lgtm",
        "looks good",
        "approved",
    ]
    if any(sig in lower for sig in review_signals):
        return AgentOutputType.REVIEW

    return AgentOutputType.UNKNOWN


def parse_agent_output(output: str) -> ParsedAgentOutput:
    """Parse raw agent output into structured form."""
    output_type = classify_output(output)
    parsed = ParsedAgentOutput(raw=output, output_type=output_type)

    lines = output.split("\n")

    # Extract code blocks
    in_code = False
    current_block: list[str] = []
    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                parsed.code_blocks.append("\n".join(current_block))
                current_block = []
                in_code = False
            else:
                in_code = True
        elif in_code:
            current_block.append(line)

    # Extract suggestions (numbered or bulleted)
    for line in lines:
        stripped = line.strip()
        if stripped and (
            (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".)")
            or stripped.startswith(("- ", "* ", "• "))
        ):
            parsed.suggestions.append(stripped)

    # Extract clarification questions
    for line in lines:
        stripped = line.strip()
        if stripped.endswith("?") and len(stripped) > 10:
            parsed.clarification_questions.append(stripped)

    # Extract file references
    import re

    file_pattern = re.compile(r"`([^`]+\.(py|js|ts|java|go|rs|cpp|h|yaml|json|md))`")
    for match in file_pattern.findall(output):
        parsed.files_mentioned.append(match[0])

    return parsed
