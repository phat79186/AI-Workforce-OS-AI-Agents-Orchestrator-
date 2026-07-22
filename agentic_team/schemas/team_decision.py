"""Schemas for agentic team routing decisions and turn output.

Defines the expected JSON structure agents should return, with
validation and normalization for malformed responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TeamAction(Enum):
    """Valid actions in a team routing decision."""

    MESSAGE = "message"
    FINALIZE = "finalize"


class TurnOutcomeType(Enum):
    """Classification of a turn's outcome."""

    ROUTED = "routed"  # Message sent to another role
    FINALIZED = "finalized"  # Lead delivered to user
    ERROR_RECOVERED = "error_recovered"  # Agent failed, routed to lead
    ESCALATED = "escalated"  # Repeated routing detected
    CLARIFICATION = "clarification"  # Agent asked a question


@dataclass
class TeamDecision:
    """Parsed and normalized routing decision from an agent."""

    action: TeamAction
    to_role: str | None
    message: str
    final_response: str
    raw_output: str
    was_privilege_downgraded: bool = False  # Non-lead tried to finalize
    was_role_corrected: bool = False  # Invalid to_role corrected to lead
    was_escalated: bool = False  # Repeated route detected

    @property
    def is_finalize(self) -> bool:
        """Check if action is FINALIZE."""
        return self.action == TeamAction.FINALIZE

    @property
    def has_clarification(self) -> bool:
        """Check if message contains clarification requests."""
        lower = self.message.lower()
        return any(
            q in lower
            for q in [
                "could you clarify",
                "can you specify",
                "do you want",
                "should i",
                "which approach",
                "before i proceed",
            ]
        )


@dataclass
class TurnResult:
    """Full result of a single team turn."""

    turn: int
    from_role: str
    to_role: str
    action: TeamAction
    agent_used: str
    decision: TeamDecision
    success: bool
    error: str | None = None
    outcome_type: TurnOutcomeType = TurnOutcomeType.ROUTED
    fallback_from: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert turn output to dict format."""
        return {
            "turn": self.turn,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "action": self.action.value,
            "agent": self.agent_used,
            "success": self.success,
            "error": self.error,
            "outcome_type": self.outcome_type.value,
            "was_escalated": self.decision.was_escalated,
            "has_clarification": self.decision.has_clarification,
            "fallback_from": self.fallback_from,
        }


# Expected JSON schema that agents should return
EXPECTED_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["message", "finalize"],
            "description": "Route a message to another role, or finalize and deliver to user",
        },
        "to_role": {
            "type": "string",
            "description": "Target role name (required for action=message)",
        },
        "message": {
            "type": "string",
            "description": "Content to send to the target role",
        },
        "final_response": {
            "type": "string",
            "description": "Final deliverable for the user (required for action=finalize)",
        },
    },
    "required": ["action"],
}
