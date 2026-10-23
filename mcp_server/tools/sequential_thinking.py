"""Sequential Thinking MCP tools for reflective, structured, and dynamic reasoning."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mcp_server.compat import Context
from orchestrator.integrations.sequential_thinking import SequentialThinkingEngine

logger = logging.getLogger(__name__)

# Module-level engine instance to retain session thoughts across tool calls
_engine = SequentialThinkingEngine()


def get_sequential_thinking_engine() -> SequentialThinkingEngine:
    """Get the active SequentialThinkingEngine instance."""
    return _engine


async def sequentialthinking(
    thought: str,
    thoughtNumber: int,
    totalThoughts: int,
    nextThoughtNeeded: bool,
    isRevision: bool = False,
    revisesThought: Optional[int] = None,
    branchFromThought: Optional[int] = None,
    branchId: Optional[str] = None,
    needsMoreThoughts: bool = False,
    resetSession: bool = False,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """A detailed tool for dynamic and reflective problem-solving through a structured, step-by-step thinking process.

    Args:
        thought: Your current thinking step or analysis.
        thoughtNumber: The current thought number (1-based integer).
        totalThoughts: The current estimate of total thoughts needed.
        nextThoughtNeeded: True if another thought step is needed to reach the conclusion.
        isRevision: Whether this thought revises or re-evaluates a previous thought.
        revisesThought: The thought number being reconsidered/revised.
        branchFromThought: The thought number from which to branch an alternative hypothesis.
        branchId: Identifier for this alternative branch of thinking.
        needsMoreThoughts: True if more thoughts are needed beyond the initial estimate.
        resetSession: Optional flag to clear prior thought history and start a fresh sequence.
        ctx: Optional MCP Context.

    Returns:
        Structured dictionary indicating thought progress, active branches, and history count.
    """
    if resetSession:
        _engine.reset()

    try:
        return _engine.process_thought(
            thought=thought,
            thought_number=thoughtNumber,
            total_thoughts=totalThoughts,
            next_thought_needed=nextThoughtNeeded,
            is_revision=isRevision,
            revises_thought=revisesThought,
            branch_from_thought=branchFromThought,
            branch_id=branchId,
            needs_more_thoughts=needsMoreThoughts,
        )
    except Exception as e:
        logger.error("Error processing sequential thought: %s", e)
        return {"error": str(e), "status": "error"}


async def sequential_thinking(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool,
    is_revision: bool = False,
    revises_thought: Optional[int] = None,
    branch_from_thought: Optional[int] = None,
    branch_id: Optional[str] = None,
    needs_more_thoughts: bool = False,
    reset_session: bool = False,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Snake_case alias for sequentialthinking tool."""
    return await sequentialthinking(
        thought=thought,
        thoughtNumber=thought_number,
        totalThoughts=total_thoughts,
        nextThoughtNeeded=next_thought_needed,
        isRevision=is_revision,
        revisesThought=revises_thought,
        branchFromThought=branch_from_thought,
        branchId=branch_id,
        needsMoreThoughts=needs_more_thoughts,
        resetSession=reset_session,
        ctx=ctx,
    )


def register_sequential_thinking_tools(mcp: Any) -> None:
    """Register sequential thinking tools with MCP server."""
    mcp.tool()(sequentialthinking)
    mcp.tool()(sequential_thinking)
