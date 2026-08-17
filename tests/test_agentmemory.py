"""Tests for the agentmemory persistent memory provider."""

from __future__ import annotations

import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestOrchestratorAgentMemory:
    """Test agentmemory integration in orchestrator context."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path

    def test_provider_initialization(self, temp_db):
        """Should initialize MemoryManager with agentmemory provider."""
        from orchestrator.context.memory_manager import MemoryManager

        manager = MemoryManager(db_path=temp_db, provider="agentmemory")
        assert manager.provider == "agentmemory"
        manager.close()

    def test_sync_to_agentmemory_mock(self, temp_db):
        """Should call agentmemory.create_memory on node creation."""
        from orchestrator.context.memory_manager import MemoryManager

        mock_agentmemory = MagicMock()
        with patch.dict(sys.modules, {"agentmemory": mock_agentmemory}):
            manager = MemoryManager(db_path=temp_db, provider="agentmemory")
            node_id = manager.store_conversation(
                messages=[{"role": "user", "content": "Hello, agent!"}],
                summary="Greeting",
            )
            assert node_id is not None
            assert mock_agentmemory.create_memory.called
            call_kwargs = mock_agentmemory.create_memory.call_args[1]
            assert call_kwargs["category"] == "conversation"
            assert "Hello, agent!" in call_kwargs["document"]
            assert call_kwargs["metadata"]["title"] == "Greeting"
            manager.close()

    def test_search_agentmemory_mock(self, temp_db):
        """Should retrieve and reconstruct SearchResult from agentmemory."""
        from orchestrator.context.memory_manager import MemoryManager
        from orchestrator.context.models.schemas import NodeType

        mock_agentmemory = MagicMock()
        mock_agentmemory.search_memory.return_value = [
            {
                "id": "mem-1",
                "document": "Authentication logic using JWT",
                "metadata": {
                    "id": "node-auth-1",
                    "node_type": "task",
                    "title": "Auth Task",
                    "project_id": "proj-123",
                    "importance_score": 1.5,
                },
                "distance": 0.2,
            }
        ]

        with patch.dict(sys.modules, {"agentmemory": mock_agentmemory}):
            manager = MemoryManager(db_path=temp_db, provider="agentmemory")
            results = manager.search("JWT authentication", limit=5, node_types=[NodeType.TASK])

            assert len(results) == 1
            res = results[0]
            assert res.match_type == "agentmemory"
            assert res.node.id == "node-auth-1"
            assert res.node.node_type == NodeType.TASK
            assert res.node.title == "Auth Task"
            assert res.score > 0.8
            manager.close()


class TestAgenticTeamAgentMemory:
    """Test agentmemory integration in agentic_team context."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        yield path

    def test_provider_initialization(self, temp_db):
        """Should initialize agentic_team MemoryManager with agentmemory provider."""
        from agentic_team.context.memory_manager import MemoryManager

        manager = MemoryManager(db_path=temp_db, provider="agentmemory")
        assert manager.provider == "agentmemory"
        manager.close()

    def test_sync_to_agentmemory_mock(self, temp_db):
        """Should call agentmemory.create_memory on task store."""
        from agentic_team.context.memory_manager import MemoryManager

        mock_agentmemory = MagicMock()
        with patch.dict(sys.modules, {"agentmemory": mock_agentmemory}):
            manager = MemoryManager(db_path=temp_db, provider="agentmemory")
            node_id = manager.store_task(
                task_description="Build API endpoint",
                outcome="Endpoint created successfully",
                success=True,
                duration_ms=1200,
            )
            assert node_id is not None
            assert mock_agentmemory.create_memory.called
            call_kwargs = mock_agentmemory.create_memory.call_args[1]
            assert call_kwargs["category"] == "task"
            assert call_kwargs["document"] == "Endpoint created successfully"
            manager.close()

    def test_search_agentmemory_mock(self, temp_db):
        """Should search agentic_team context using agentmemory."""
        from agentic_team.context.memory_manager import MemoryManager
        from agentic_team.context.models.schemas import NodeType

        mock_agentmemory = MagicMock()
        mock_agentmemory.search_memory.return_value = [
            {
                "id": "mem-2",
                "document": "Fixed SQL injection bug",
                "metadata": {
                    "id": "mistake-sql-1",
                    "node_type": "mistake",
                    "title": "Mistake: security",
                    "importance_score": 2.0,
                },
                "distance": 0.1,
            }
        ]

        with patch.dict(sys.modules, {"agentmemory": mock_agentmemory}):
            manager = MemoryManager(db_path=temp_db, provider="agentmemory")
            results = manager.search("SQL injection", limit=5, node_types=[NodeType.MISTAKE])

            assert len(results) == 1
            res = results[0]
            assert res.match_type == "agentmemory"
            assert res.node.id == "mistake-sql-1"
            assert res.node.node_type == NodeType.MISTAKE
            assert res.score > 0.9
            manager.close()
