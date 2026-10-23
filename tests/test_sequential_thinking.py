"""Tests for the Sequential Thinking integration and MCP tools."""

import pytest

from mcp_server.tools.sequential_thinking import (
    get_sequential_thinking_engine,
    sequential_thinking,
    sequentialthinking,
)
from orchestrator.integrations.ecosystem_hub import ExternalEcosystemHub
from orchestrator.integrations.sequential_thinking import SequentialThinkingEngine, ThoughtData


class TestSequentialThinkingEngine:
    """Test suite for SequentialThinkingEngine core logic."""

    def test_basic_progression(self):
        engine = SequentialThinkingEngine()
        res1 = engine.process_thought(
            thought="Step 1: Understand problem scope.",
            thought_number=1,
            total_thoughts=2,
            next_thought_needed=True,
        )
        assert res1["thought_number"] == 1
        assert res1["total_thoughts"] == 2
        assert res1["next_thought_needed"] is True
        assert res1["status"] == "in_progress"
        assert res1["thought_history_length"] == 1

        res2 = engine.process_thought(
            thought="Step 2: Provide solution architecture.",
            thought_number=2,
            total_thoughts=2,
            next_thought_needed=False,
        )
        assert res2["thought_number"] == 2
        assert res2["next_thought_needed"] is False
        assert res2["status"] == "completed"
        assert res2["thought_history_length"] == 2

    def test_dynamic_total_thoughts_adjustment(self):
        engine = SequentialThinkingEngine()
        res = engine.process_thought(
            thought="Step 4 beyond initial total.",
            thought_number=4,
            total_thoughts=2,
            next_thought_needed=False,
        )
        assert res["total_thoughts"] == 4
        assert res["thought_number"] == 4

    def test_validation_errors(self):
        engine = SequentialThinkingEngine()
        with pytest.raises(ValueError, match="thought_number must be >= 1"):
            engine.process_thought(
                "Test", thought_number=0, total_thoughts=1, next_thought_needed=False
            )

        with pytest.raises(ValueError, match="total_thoughts must be >= 1"):
            engine.process_thought(
                "Test", thought_number=1, total_thoughts=0, next_thought_needed=False
            )

        with pytest.raises(ValueError, match="revises_thought is required"):
            engine.process_thought(
                "Revision",
                thought_number=2,
                total_thoughts=2,
                next_thought_needed=False,
                is_revision=True,
                revises_thought=None,
            )

    def test_revision_flow(self):
        engine = SequentialThinkingEngine()
        engine.process_thought("Initial hypothesis", 1, 2, True)
        res_rev = engine.process_thought(
            thought="Correction: Previous assumption was invalid.",
            thought_number=2,
            total_thoughts=3,
            next_thought_needed=True,
            is_revision=True,
            revises_thought=1,
        )
        assert res_rev["is_revision"] is True
        assert res_rev["revises_thought"] == 1
        summary = engine.get_summary()
        assert "Revising Step 1" in summary

    def test_branching_flow(self):
        engine = SequentialThinkingEngine()
        engine.process_thought("Base setup", 1, 3, True)
        res_branch = engine.process_thought(
            thought="Alternative branch B",
            thought_number=2,
            total_thoughts=3,
            next_thought_needed=True,
            branch_from_thought=1,
            branch_id="alt-hyp-b",
        )
        assert "alt-hyp-b" in res_branch["branches"]
        assert "alt-hyp-b" in engine.branches
        # The branch should contain thought 1 plus the new thought 2
        assert len(engine.branches["alt-hyp-b"]) == 2

    def test_reset_and_history(self):
        engine = SequentialThinkingEngine()
        engine.process_thought("Thought 1", 1, 1, False)
        assert len(engine.get_history()) == 1
        engine.reset()
        assert len(engine.get_history()) == 0
        assert engine.get_summary() == "No sequential thoughts recorded."


class TestSequentialThinkingMCP:
    """Test suite for MCP server tool registration and endpoints."""

    @pytest.mark.asyncio
    async def test_sequentialthinking_tool(self):
        res1 = await sequentialthinking(
            thought="Analyze system latency",
            thoughtNumber=1,
            totalThoughts=2,
            nextThoughtNeeded=True,
            resetSession=True,
        )
        assert res1["thought_number"] == 1
        assert res1["status"] == "in_progress"

        res2 = await sequential_thinking(
            thought="Diagnose DB slow query log",
            thought_number=2,
            total_thoughts=2,
            next_thought_needed=False,
        )
        assert res2["thought_number"] == 2
        assert res2["status"] == "completed"

    @pytest.mark.asyncio
    async def test_sequentialthinking_error_handling(self):
        res = await sequentialthinking(
            thought="Invalid thought",
            thoughtNumber=-1,
            totalThoughts=1,
            nextThoughtNeeded=False,
        )
        assert "error" in res
        assert res["status"] == "error"


class TestEcosystemHubIntegration:
    """Test integration into ExternalEcosystemHub."""

    def test_hub_has_sequential_thinking(self):
        hub = ExternalEcosystemHub()
        assert isinstance(hub.sequential_thinking, SequentialThinkingEngine)
        status = hub.get_status()
        assert status["sequential_thinking_status"] == "READY"
        assert "sequential_thinking_history_length" in status
