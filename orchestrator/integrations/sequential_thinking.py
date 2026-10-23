"""Sequential Thinking integration for reflective, dynamic, and branched multi-step reasoning.

Imported and adapted from the Model Context Protocol reference server:
https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThoughtData:
    """Structure representing a single reasoning step in a sequential thought chain."""

    thought: str
    thought_number: int
    total_thoughts: int
    next_thought_needed: bool
    is_revision: bool = False
    revises_thought: Optional[int] = None
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None
    needs_more_thoughts: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert thought data to dictionary."""
        return asdict(self)


class SequentialThinkingEngine:
    """Core engine managing iterative thought progression, revision, and branch exploration."""

    def __init__(self) -> None:
        """Initialize an empty thought history and branch store."""
        self.thought_history: List[Dict[str, Any]] = []
        self.branches: Dict[str, List[Dict[str, Any]]] = {}
        self.current_branch: Optional[str] = None

    def reset(self) -> None:
        """Reset the thought history and active branches for a fresh problem session."""
        self.thought_history.clear()
        self.branches.clear()
        self.current_branch = None

    def process_thought(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        is_revision: bool = False,
        revises_thought: Optional[int] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        needs_more_thoughts: bool = False,
    ) -> Dict[str, Any]:
        """Process and validate a single thought in the sequence.

        Args:
            thought: Reasoning text for this step.
            thought_number: 1-indexed step number.
            total_thoughts: Current estimated total steps required.
            next_thought_needed: True if another step is needed before final conclusion.
            is_revision: True if this step revises a previous step's conclusion.
            revises_thought: The 1-indexed thought number being revised.
            branch_from_thought: The 1-indexed thought number from which to fork a new branch.
            branch_id: Unique identifier for the branched hypothesis path.
            needs_more_thoughts: Signal that more thoughts are required beyond initial estimate.

        Returns:
            Dictionary containing updated session state, history length, and active branches.
        """
        if thought_number < 1:
            raise ValueError(f"thought_number must be >= 1, got {thought_number}")

        if total_thoughts < 1:
            raise ValueError(f"total_thoughts must be >= 1, got {total_thoughts}")

        # Dynamically adjust total_thoughts if current step exceeds estimate
        if thought_number > total_thoughts:
            total_thoughts = thought_number

        if is_revision and revises_thought is None:
            raise ValueError("revises_thought is required when is_revision is True")

        # Handle branching
        if branch_from_thought is not None:
            if not branch_id:
                branch_id = f"branch_from_{branch_from_thought}"
            self.current_branch = branch_id

            if branch_id not in self.branches:
                # Seed the new branch with thoughts up to the branch point
                fork_history = [
                    t
                    for t in self.thought_history
                    if t.get("thought_number", 0) <= branch_from_thought
                ]
                self.branches[branch_id] = list(fork_history)

        data = ThoughtData(
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            is_revision=is_revision,
            revises_thought=revises_thought,
            branch_from_thought=branch_from_thought,
            branch_id=branch_id or self.current_branch,
            needs_more_thoughts=needs_more_thoughts,
        )

        record = data.to_dict()
        self.thought_history.append(record)

        if self.current_branch and self.current_branch in self.branches:
            self.branches[self.current_branch].append(record)

        return {
            "thought_number": thought_number,
            "total_thoughts": total_thoughts,
            "next_thought_needed": next_thought_needed,
            "branches": list(self.branches.keys()),
            "thought_history_length": len(self.thought_history),
            "current_branch": self.current_branch,
            "is_revision": is_revision,
            "revises_thought": revises_thought,
            "status": "in_progress" if next_thought_needed else "completed",
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the complete sequence of thoughts recorded so far."""
        return list(self.thought_history)

    def get_summary(self) -> str:
        """Generate a formatted markdown audit log of the reasoning trajectory."""
        if not self.thought_history:
            return "No sequential thoughts recorded."

        lines = ["### Sequential Thinking Summary", ""]
        for item in self.thought_history:
            prefix = f"**Step {item['thought_number']}/{item['total_thoughts']}**"
            if item.get("is_revision"):
                prefix += f" *(Revising Step {item.get('revises_thought')})*"
            if item.get("branch_id"):
                prefix += f" `[Branch: {item['branch_id']}]`"

            lines.append(f"{prefix}: {item['thought']}")

        status = (
            "Completed"
            if not self.thought_history[-1].get("next_thought_needed")
            else "In Progress"
        )
        lines.append("")
        lines.append(f"**Final Status**: {status} ({len(self.thought_history)} steps recorded)")
        if self.branches:
            lines.append(f"**Explored Branches**: {', '.join(self.branches.keys())}")

        return "\n".join(lines)
