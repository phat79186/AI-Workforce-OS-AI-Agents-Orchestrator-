"""Tests for the context graph system."""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Test imports - these will fail if dependencies aren't installed
# but the tests are optional
pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed")


class TestGraphStore:
    """Tests for the GraphStore class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def graph_store(self, temp_db):
        """Create a GraphStore instance with temp database."""
        from orchestrator.context.graph_store import GraphStore

        return GraphStore(temp_db)

    def test_create_graph_store(self, graph_store):
        """Should create a graph store with schema."""
        from orchestrator.context.graph_store import GraphStore

        assert isinstance(graph_store, GraphStore)

    def test_add_node(self, graph_store):
        """Should add a node to the graph."""
        from orchestrator.context.schemas import ConversationNode

        node = ConversationNode(
            id="test-conv-1",
            content="Test conversation content",
            timestamp=datetime.now(timezone.utc),
            metadata={"user": "test"},
        )

        node_id = graph_store.add_node(node)
        assert node_id == "test-conv-1"

    def test_get_node(self, graph_store):
        """Should retrieve a node by ID."""
        from orchestrator.context.schemas import TaskNode

        node = TaskNode(
            id="test-task-1",
            content="Test task content",
            timestamp=datetime.now(timezone.utc),
            task_description="Build feature",
            outcome="completed",
            success=True,
        )

        graph_store.add_node(node)
        retrieved = graph_store.get_node("test-task-1")

        assert retrieved is not None
        assert retrieved.id == "test-task-1"
        assert retrieved.content == "Test task content"

    def test_add_edge(self, graph_store):
        """Should add an edge between nodes."""
        from orchestrator.context.schemas import ConversationNode, EdgeType

        node1 = ConversationNode(
            id="conv-1",
            content="First conversation",
            timestamp=datetime.now(timezone.utc),
        )
        node2 = ConversationNode(
            id="conv-2",
            content="Second conversation",
            timestamp=datetime.now(timezone.utc),
        )

        graph_store.add_node(node1)
        graph_store.add_node(node2)
        graph_store.add_edge("conv-1", "conv-2", EdgeType.FOLLOWED_BY)

        edges = graph_store.get_edges("conv-1")
        assert len(edges) == 1
        assert edges[0]["target_id"] == "conv-2"
        assert edges[0]["edge_type"] == "FOLLOWED_BY"

    def test_full_text_search(self, graph_store):
        """Should find nodes using full-text search."""
        from orchestrator.context.schemas import TaskNode

        node1 = TaskNode(
            id="task-1",
            content="Implement user authentication with JWT tokens",
            timestamp=datetime.now(timezone.utc),
            task_description="Auth feature",
            outcome="completed",
            success=True,
        )
        node2 = TaskNode(
            id="task-2",
            content="Build database schema for orders",
            timestamp=datetime.now(timezone.utc),
            task_description="DB schema",
            outcome="completed",
            success=True,
        )

        graph_store.add_node(node1)
        graph_store.add_node(node2)

        # Search for authentication
        results = graph_store.full_text_search("authentication JWT")
        assert len(results) >= 1
        assert any(r.id == "task-1" for r in results)

    def test_delete_node(self, graph_store):
        """Should delete a node and its edges."""
        from orchestrator.context.schemas import ConversationNode

        node = ConversationNode(
            id="to-delete",
            content="Temporary content",
            timestamp=datetime.now(timezone.utc),
        )

        graph_store.add_node(node)
        assert graph_store.get_node("to-delete") is not None

        graph_store.delete_node("to-delete")
        assert graph_store.get_node("to-delete") is None


class TestBM25Index:
    """Tests for the BM25 index."""

    def test_index_and_search(self):
        """Should index documents and return ranked results."""
        from orchestrator.context.bm25_index import BM25Index

        index = BM25Index()

        # Add some documents
        index.add_document("doc1", "python programming language tutorial")
        index.add_document("doc2", "javascript web development guide")
        index.add_document("doc3", "python web framework flask tutorial")

        # Search for python
        results = index.search("python programming", limit=3)

        assert len(results) >= 1
        # doc1 and doc3 should rank higher since they contain "python"
        doc_ids = [r[0] for r in results]
        assert "doc1" in doc_ids or "doc3" in doc_ids

    def test_remove_document(self):
        """Should remove document from index."""
        from orchestrator.context.bm25_index import BM25Index

        index = BM25Index()
        index.add_document("doc1", "test content")
        index.remove_document("doc1")

        results = index.search("test content", limit=5)
        doc_ids = [r[0] for r in results]
        assert "doc1" not in doc_ids


class TestHybridSearch:
    """Tests for hybrid search combining BM25 and semantic."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_hybrid_search_combines_results(self, temp_db):
        """Should combine BM25 and semantic search results."""
        from orchestrator.context.graph_store import GraphStore
        from orchestrator.context.hybrid_search import HybridSearchEngine
        from orchestrator.context.schemas import TaskNode

        graph_store = GraphStore(temp_db)
        hybrid = HybridSearchEngine(graph_store)

        # Add test nodes
        node1 = TaskNode(
            id="task-1",
            content="Implement REST API endpoints for user management",
            timestamp=datetime.now(timezone.utc),
            task_description="User API",
            outcome="completed",
            success=True,
        )
        node2 = TaskNode(
            id="task-2",
            content="Write unit tests for authentication module",
            timestamp=datetime.now(timezone.utc),
            task_description="Auth tests",
            outcome="completed",
            success=True,
        )

        graph_store.add_node(node1)
        graph_store.add_node(node2)
        hybrid.index_node(node1)
        hybrid.index_node(node2)

        # Search should return relevant results
        results = hybrid.search("API endpoints REST", limit=5)

        assert len(results) >= 1
        # task-1 should be in results since it matches the query


class TestMemoryManager:
    """Tests for the high-level MemoryManager API."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def memory_manager(self, temp_db):
        """Create a MemoryManager with temp database."""
        from orchestrator.context.memory_manager import MemoryManager

        return MemoryManager(db_path=temp_db)

    def test_store_conversation(self, memory_manager):
        """Should store a conversation in context."""
        conv_id = memory_manager.store_conversation(
            content="User asked about authentication",
            metadata={"topic": "auth"},
        )

        assert conv_id is not None
        assert len(conv_id) > 0

    def test_store_task(self, memory_manager):
        """Should store a task with outcome."""
        task_id = memory_manager.store_task(
            task_description="Build login form",
            outcome="completed",
            success=True,
            metadata={"component": "frontend"},
        )

        assert task_id is not None

    def test_log_mistake(self, memory_manager):
        """Should log a mistake for learning."""
        mistake_id = memory_manager.log_mistake(
            error_description="Used wrong API endpoint",
            context="Was trying to fetch user data",
            correction="Use /api/v1/users instead of /api/users",
        )

        assert mistake_id is not None

    def test_search(self, memory_manager):
        """Should search across stored context."""
        # Store some data
        memory_manager.store_task(
            task_description="Implement JWT authentication",
            outcome="completed",
            success=True,
        )
        memory_manager.store_task(
            task_description="Build order processing system",
            outcome="completed",
            success=True,
        )

        # Search for authentication
        results = memory_manager.search("JWT authentication tokens", limit=5)

        assert len(results) >= 1

    def test_get_relevant_context(self, memory_manager):
        """Should get relevant context for a query."""
        # Store some context
        memory_manager.store_conversation(
            content="Discussion about database schema design",
        )
        memory_manager.store_task(
            task_description="Create PostgreSQL schema",
            outcome="completed",
            success=True,
        )

        # Get relevant context
        context = memory_manager.get_relevant_context(
            query="database schema",
            limit=5,
        )

        assert isinstance(context, str)
        # Context may be empty if no matches; that's valid
        assert context is not None

    def test_link_nodes(self, memory_manager):
        """Should link related nodes."""
        from orchestrator.context.schemas import EdgeType

        id1 = memory_manager.store_task(
            task_description="Task 1",
            outcome="completed",
            success=True,
        )
        id2 = memory_manager.store_task(
            task_description="Task 2",
            outcome="completed",
            success=True,
        )

        # Link them
        memory_manager.link_nodes(id1, id2, EdgeType.RELATED_TO)

        # Verify link exists
        related = memory_manager.get_related_nodes(id1, EdgeType.RELATED_TO)
        assert len(related) >= 1


class TestSchemas:
    """Tests for context schema definitions."""

    def test_conversation_node_creation(self):
        """Should create a valid ConversationNode."""
        from orchestrator.context.schemas import ConversationNode

        node = ConversationNode(
            id="conv-test",
            content="Test conversation",
            timestamp=datetime.now(timezone.utc),
            metadata={"key": "value"},
        )

        assert node.id == "conv-test"
        assert node.type == "conversation"
        assert node.content == "Test conversation"

    def test_task_node_creation(self):
        """Should create a valid TaskNode."""
        from orchestrator.context.schemas import TaskNode

        node = TaskNode(
            id="task-test",
            content="Task content",
            timestamp=datetime.now(timezone.utc),
            task_description="Do something",
            outcome="completed",
            success=True,
            metadata={"duration": 100},
        )

        assert node.id == "task-test"
        assert node.type == "task"
        assert node.success is True

    def test_mistake_node_creation(self):
        """Should create a valid MistakeNode."""
        from orchestrator.context.schemas import MistakeNode

        node = MistakeNode(
            id="mistake-test",
            content="Error description",
            timestamp=datetime.now(timezone.utc),
            error_description="Made an error",
            context="While doing X",
            correction="Should have done Y",
        )

        assert node.id == "mistake-test"
        assert node.type == "mistake"
        assert node.correction == "Should have done Y"

    def test_edge_types(self):
        """Should have all expected edge types."""
        from orchestrator.context.schemas import EdgeType

        expected_types = [
            "RELATED_TO",
            "CAUSED_BY",
            "FIXED_BY",
            "SIMILAR_TO",
            "DEPENDS_ON",
            "PRECEDED_BY",
            "FOLLOWED_BY",
            "LEARNED_FROM",
            "REFERENCES",
            "CONTAINS",
            "PRODUCED_BY",
            "USED_IN",
        ]

        for edge_type in expected_types:
            assert hasattr(EdgeType, edge_type)


class TestEmbeddings:
    """Tests for embedding generation."""

    def test_generate_embedding(self):
        """Should generate embeddings for text."""
        from orchestrator.context.embeddings import EmbeddingGenerator

        generator = EmbeddingGenerator()
        embedding = generator.generate("Test text for embedding")

        assert embedding is not None
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension

    def test_embedding_similarity(self):
        """Similar texts should have similar embeddings."""
        import numpy as np

        from orchestrator.context.embeddings import EmbeddingGenerator

        generator = EmbeddingGenerator()

        emb1 = np.array(generator.generate("Python programming tutorial"))
        emb2 = np.array(generator.generate("Python coding guide"))
        emb3 = np.array(generator.generate("Cooking recipe for pasta"))

        # Cosine similarity
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_similar = cosine_sim(emb1, emb2)
        sim_different = cosine_sim(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_similar > sim_different


# ---------------------------------------------------------------------------
# Obsidian export tests
# ---------------------------------------------------------------------------


class TestObsidianExport:
    """Tests for the Obsidian vault exporter on context graphs."""

    @pytest.fixture
    def populated_exporter(self, tmp_path):
        """Create a ContextExporter with a populated graph store."""
        import json as _json

        from orchestrator.context.graph_store import GraphStore
        from orchestrator.context.ops.export import ContextExporter
        from orchestrator.context.schemas import (
            ConversationNode,
            DecisionNode,
            EdgeType,
            MistakeNode,
            PatternNode,
            TaskNode,
        )

        db_path = str(tmp_path / "test_ctx.db")
        store = GraphStore(db_path)
        now = datetime.now(timezone.utc)

        task = TaskNode(
            id="task-1",
            content="Implement authentication module",
            timestamp=now,
            task_description="Build JWT auth",
            outcome="completed",
            success=True,
            tags=["auth", "security"],
        )
        decision = DecisionNode(
            id="dec-1",
            content="Use SQLite for storage",
            timestamp=now,
            decision="SQLite",
            rationale="Simple, embedded, no external deps",
            alternatives=["PostgreSQL", "MongoDB"],
        )
        mistake = MistakeNode(
            id="mis-1",
            content="Used string formatting in SQL",
            timestamp=now,
            description="SQL injection risk",
            correction="Parameterized queries",
            prevention="Always use ? placeholders",
        )
        pattern = PatternNode(
            id="pat-1",
            content="Adapter pattern for tool integration",
            timestamp=now,
            pattern_name="Adapter",
            language="python",
            use_case="Wrapping external CLIs",
        )
        conv = ConversationNode(
            id="conv-1",
            content="Discussion about auth architecture",
            timestamp=now,
        )

        for node in [task, decision, mistake, pattern, conv]:
            store.add_node(node)

        store.add_edge("task-1", "dec-1", EdgeType.RELATED_TO)
        store.add_edge("dec-1", "mis-1", EdgeType.CAUSED_BY)
        store.add_edge("pat-1", "task-1", EdgeType.USED_IN)

        exporter = ContextExporter(store)
        yield exporter, store

    def test_export_obsidian_creates_vault(self, populated_exporter, tmp_path):
        """Should create vault directory with notes."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        result = exporter.export_obsidian(vault_dir)

        from pathlib import Path

        assert result["notes_written"] == 5
        assert result["output_path"] == vault_dir
        assert Path(vault_dir).is_dir()

    def test_export_obsidian_index(self, populated_exporter, tmp_path):
        """Should create _Index.md with stats and categories."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        exporter.export_obsidian(vault_dir)

        from pathlib import Path

        index = Path(vault_dir) / "_Index.md"
        assert index.is_file()
        text = index.read_text(encoding="utf-8")
        assert "Context Graph" in text
        assert "Nodes" in text
        assert "Edges" in text

    def test_export_obsidian_graph_config(self, populated_exporter, tmp_path):
        """Should create .obsidian/ config with graph colors."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        exporter.export_obsidian(vault_dir)

        import json as _json
        from pathlib import Path

        obs = Path(vault_dir) / ".obsidian"
        assert obs.is_dir()

        graph_json = _json.loads((obs / "graph.json").read_text(encoding="utf-8"))
        assert "colorGroups" in graph_json
        assert len(graph_json["colorGroups"]) > 0

        plugins = _json.loads((obs / "core-plugins.json").read_text(encoding="utf-8"))
        assert isinstance(plugins, list)
        assert "graph" in plugins

    def test_export_obsidian_frontmatter(self, populated_exporter, tmp_path):
        """Notes should have YAML frontmatter with type and tags."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        exporter.export_obsidian(vault_dir)

        from pathlib import Path

        md_files = [f for f in Path(vault_dir).rglob("*.md") if f.name != "_Index.md"]
        assert len(md_files) == 5

        for note in md_files:
            text = note.read_text(encoding="utf-8")
            assert text.startswith("---"), f"{note.name} missing frontmatter"
            assert "type:" in text

    def test_export_obsidian_wikilinks(self, populated_exporter, tmp_path):
        """Notes with relationships should contain [[wikilinks]]."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        exporter.export_obsidian(vault_dir)

        from pathlib import Path

        all_text = ""
        for f in Path(vault_dir).rglob("*.md"):
            all_text += f.read_text(encoding="utf-8")
        assert "[[" in all_text and "]]" in all_text

    def test_export_obsidian_node_type_filter(self, populated_exporter, tmp_path):
        """Filtering by node_types should only export those types."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        result = exporter.export_obsidian(vault_dir, node_types=["task"])

        assert result["notes_written"] == 1

    def test_export_obsidian_folder_layout(self, populated_exporter, tmp_path):
        """Notes should be organized in typed folders."""
        exporter, _ = populated_exporter
        vault_dir = str(tmp_path / "vault")
        exporter.export_obsidian(vault_dir)

        from pathlib import Path

        vault = Path(vault_dir)
        dirs = {d.name for d in vault.iterdir() if d.is_dir() and not d.name.startswith(".")}
        # We inserted task, decision, mistake, pattern, conversation
        expected = {"Tasks", "Decisions", "Mistakes", "Patterns", "Conversations"}
        assert expected.issubset(dirs), f"Missing folders: {expected - dirs}"


class TestAgenticTeamObsidianExport:
    """Tests for the Agentic Team Obsidian vault exporter."""

    @pytest.fixture
    def at_exporter(self, tmp_path):
        """Create an Agentic Team ContextExporter with populated graph store."""
        from agentic_team.context.graph_store import GraphStore
        from agentic_team.context.ops.export import ContextExporter
        from agentic_team.context.schemas import ConversationNode, DecisionNode, EdgeType, TaskNode

        db_path = str(tmp_path / "at_ctx.db")
        store = GraphStore(db_path)
        now = datetime.now(timezone.utc)

        task = TaskNode(
            id="at-task-1",
            content="Team coordination task",
            timestamp=now,
            task_description="Coordinate agents",
            outcome="success",
            success=True,
        )
        decision = DecisionNode(
            id="at-dec-1",
            content="Use round-robin scheduling",
            timestamp=now,
            decision="Round-robin",
            rationale="Fair distribution",
            alternatives=["Priority-based"],
        )

        store.add_node(task)
        store.add_node(decision)
        store.add_edge("at-task-1", "at-dec-1", EdgeType.RELATED_TO)

        exporter = ContextExporter(store)
        yield exporter, store

    def test_at_export_obsidian_creates_vault(self, at_exporter, tmp_path):
        """Should create vault with notes and config."""
        exporter, _ = at_exporter
        vault_dir = str(tmp_path / "vault")
        result = exporter.export_obsidian(vault_dir)

        from pathlib import Path

        assert result["notes_written"] == 2
        assert Path(vault_dir).is_dir()
        assert (Path(vault_dir) / "_Index.md").is_file()
        assert (Path(vault_dir) / ".obsidian" / "graph.json").is_file()

    def test_at_export_obsidian_index_branding(self, at_exporter, tmp_path):
        """Index should reference Agentic Team branding."""
        exporter, _ = at_exporter
        vault_dir = str(tmp_path / "vault")
        exporter.export_obsidian(vault_dir)

        from pathlib import Path

        text = (Path(vault_dir) / "_Index.md").read_text(encoding="utf-8")
        assert "Agentic Team" in text
