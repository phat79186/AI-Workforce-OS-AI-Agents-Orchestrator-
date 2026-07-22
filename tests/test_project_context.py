"""Tests for project context system — scanning, multi-project isolation, and graph building."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest


class TestProjectScanner:
    """Tests for the project scanner module."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a minimal sample project directory."""
        # Python project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "src" / "__init__.py").write_text("")
        (tmp_path / "src" / "main.py").write_text("def main(): pass")
        (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
        (tmp_path / "tests" / "test_main.py").write_text("def test_main(): pass")
        (tmp_path / "requirements.txt").write_text("flask>=2.0\npytest>=7.0\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "sample"\n[tool.pytest.ini_options]\n'
        )
        (tmp_path / "README.md").write_text("# Sample Project\nA test project.")
        (tmp_path / "Makefile").write_text("test:\n\tpytest")
        (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")
        return tmp_path

    @pytest.fixture
    def js_project(self, tmp_path):
        """Create a minimal JS project directory."""
        proj = tmp_path / "jsapp"
        proj.mkdir()
        (proj / "src").mkdir()
        (proj / "src" / "index.ts").write_text("export const x = 1;")
        (proj / "src" / "app.tsx").write_text("export default function App() {}")
        (proj / "package.json").write_text(
            json.dumps(
                {
                    "name": "jsapp",
                    "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
                    "devDependencies": {"jest": "^29.0.0", "typescript": "^5.0.0"},
                }
            )
        )
        (proj / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}')
        return proj

    def test_scanner_creates_project_node(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        assert result["project_node"] is not None
        assert result["project_node"].project_name == sample_project.name
        assert result["project_node"].project_id != ""
        assert result["project_node"].file_count > 0

    def test_scanner_detects_languages(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        assert "python" in result["project_node"].languages

    def test_scanner_detects_frameworks(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        frameworks = result["project_node"].frameworks
        assert "python" in frameworks or "pytest" in frameworks

    def test_scanner_creates_file_nodes(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        assert len(result["file_nodes"]) > 0

    def test_scanner_creates_pattern_nodes(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        assert len(result["pattern_nodes"]) > 0

    def test_scanner_creates_edges(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        assert len(result["edges"]) > 0

    def test_scanner_project_id_deterministic(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner, generate_project_id

        pid1 = generate_project_id(str(sample_project))
        pid2 = generate_project_id(str(sample_project))
        assert pid1 == pid2
        assert len(pid1) == 16

    def test_scanner_different_paths_different_ids(self, sample_project, js_project):
        from orchestrator.context.ops.project_scanner import generate_project_id

        pid1 = generate_project_id(str(sample_project))
        pid2 = generate_project_id(str(js_project))
        assert pid1 != pid2

    def test_scanner_js_project(self, js_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(js_project))
        result = scanner.scan()
        node = result["project_node"]
        assert "typescript" in node.languages or "tsx" in node.languages
        assert any(fw in node.frameworks for fw in ["react", "jest", "node", "typescript"])

    def test_scanner_invalid_path_raises(self):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        with pytest.raises(ValueError, match="not a directory"):
            ProjectScanner("/nonexistent/path/12345")

    def test_scanner_skips_hidden_dirs(self, sample_project):
        (sample_project / ".git").mkdir()
        (sample_project / ".git" / "config").write_text("gitconfig")
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        dir_names = [n.metadata.get("directory", "") for n in result["file_nodes"]]
        assert not any(".git" in d.split(os.sep) for d in dir_names)

    def test_scanner_summary_has_all_keys(self, sample_project):
        from orchestrator.context.ops.project_scanner import ProjectScanner

        scanner = ProjectScanner(str(sample_project))
        result = scanner.scan()
        summary = result["summary"]
        assert "project_name" in summary
        assert "project_id" in summary
        assert "total_files" in summary
        assert "languages" in summary
        assert "frameworks" in summary


class TestProjectScopedMemoryManager:
    """Tests for project-scoped MemoryManager operations."""

    @pytest.fixture
    def temp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def manager(self, temp_db):
        from orchestrator.context.memory_manager import MemoryManager

        return MemoryManager(db_path=temp_db, auto_embed=False, auto_index=True)

    @pytest.fixture
    def sample_project(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("print('hello')")
        (tmp_path / "requirements.txt").write_text("flask\n")
        (tmp_path / "README.md").write_text("# Test")
        return tmp_path

    def test_register_project(self, manager, sample_project):
        pid = manager.register_project(str(sample_project))
        assert pid != ""
        assert len(pid) == 16

    def test_register_project_idempotent(self, manager, sample_project):
        pid1 = manager.register_project(str(sample_project))
        pid2 = manager.register_project(str(sample_project))
        assert pid1 == pid2

    def test_register_creates_project_node(self, manager, sample_project):
        from orchestrator.context.models.schemas import NodeType

        pid = manager.register_project(str(sample_project))
        nodes = manager.graph_store.query_nodes(node_type=NodeType.PROJECT, project_id=pid)
        assert len(nodes) == 1
        assert nodes[0].title.startswith("Project:")

    def test_register_creates_file_nodes(self, manager, sample_project):
        from orchestrator.context.models.schemas import NodeType

        pid = manager.register_project(str(sample_project))
        file_nodes = manager.graph_store.query_nodes(node_type=NodeType.FILE, project_id=pid)
        assert len(file_nodes) > 0

    def test_store_task_with_project_id(self, manager, sample_project):
        from orchestrator.context.models.schemas import NodeType

        pid = manager.register_project(str(sample_project))
        task_id = manager.store_task(
            task_description="Test task",
            outcome="Success",
            success=True,
            project_id=pid,
        )
        node = manager.graph_store.get_node(task_id)
        assert node is not None
        assert node.project_id == pid

    def test_get_project_context(self, manager, sample_project):
        pid = manager.register_project(str(sample_project))
        ctx = manager.get_project_context(pid)
        assert ctx["project"] is not None
        assert isinstance(ctx["patterns"], list)
        assert isinstance(ctx["files"], list)

    def test_delete_project_graph(self, manager, sample_project):
        from orchestrator.context.models.schemas import NodeType

        pid = manager.register_project(str(sample_project))
        nodes_before = manager.graph_store.query_nodes(project_id=pid)
        assert len(nodes_before) > 0
        deleted = manager.delete_project_graph(pid)
        assert deleted > 0
        nodes_after = manager.graph_store.query_nodes(project_id=pid)
        assert len(nodes_after) == 0

    def test_rescan_project(self, manager, sample_project):
        pid = manager.register_project(str(sample_project))
        # Add a file
        (sample_project / "new_file.py").write_text("x = 1")
        pid2 = manager.rescan_project(str(sample_project))
        assert pid == pid2


class TestMultiProjectIsolation:
    """Tests ensuring multiple projects don't mingle."""

    @pytest.fixture
    def temp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def manager(self, temp_db):
        from orchestrator.context.memory_manager import MemoryManager

        return MemoryManager(db_path=temp_db, auto_embed=False, auto_index=True)

    @pytest.fixture
    def project_a(self, tmp_path):
        proj = tmp_path / "project_a"
        proj.mkdir()
        (proj / "main.py").write_text("print('A')")
        (proj / "requirements.txt").write_text("django\n")
        return proj

    @pytest.fixture
    def project_b(self, tmp_path):
        proj = tmp_path / "project_b"
        proj.mkdir()
        (proj / "index.js").write_text("console.log('B')")
        (proj / "package.json").write_text('{"name": "b", "dependencies": {}}')
        return proj

    def test_two_projects_different_ids(self, manager, project_a, project_b):
        pid_a = manager.register_project(str(project_a))
        pid_b = manager.register_project(str(project_b))
        assert pid_a != pid_b

    def test_project_nodes_isolated(self, manager, project_a, project_b):
        from orchestrator.context.models.schemas import NodeType

        pid_a = manager.register_project(str(project_a))
        pid_b = manager.register_project(str(project_b))

        nodes_a = manager.graph_store.query_nodes(project_id=pid_a)
        nodes_b = manager.graph_store.query_nodes(project_id=pid_b)

        ids_a = {n.id for n in nodes_a}
        ids_b = {n.id for n in nodes_b}
        assert ids_a.isdisjoint(ids_b), "Projects should have no overlapping node IDs"

    def test_tasks_scoped_to_project(self, manager, project_a, project_b):
        from orchestrator.context.models.schemas import NodeType

        pid_a = manager.register_project(str(project_a))
        pid_b = manager.register_project(str(project_b))

        manager.store_task("Task for A", "Done A", True, project_id=pid_a)
        manager.store_task("Task for B", "Done B", True, project_id=pid_b)

        tasks_a = manager.graph_store.query_nodes(node_type=NodeType.TASK, project_id=pid_a)
        tasks_b = manager.graph_store.query_nodes(node_type=NodeType.TASK, project_id=pid_b)

        assert len(tasks_a) == 1
        assert len(tasks_b) == 1
        assert tasks_a[0].project_id == pid_a
        assert tasks_b[0].project_id == pid_b

    def test_delete_one_project_preserves_other(self, manager, project_a, project_b):
        pid_a = manager.register_project(str(project_a))
        pid_b = manager.register_project(str(project_b))

        manager.delete_project_graph(pid_a)

        nodes_a = manager.graph_store.query_nodes(project_id=pid_a)
        nodes_b = manager.graph_store.query_nodes(project_id=pid_b)
        assert len(nodes_a) == 0
        assert len(nodes_b) > 0

    def test_get_project_context_scoped(self, manager, project_a, project_b):
        pid_a = manager.register_project(str(project_a))
        pid_b = manager.register_project(str(project_b))

        ctx_a = manager.get_project_context(pid_a)
        ctx_b = manager.get_project_context(pid_b)

        assert ctx_a["project"]["project_id"] == pid_a  # type: ignore[index]
        assert ctx_b["project"]["project_id"] == pid_b  # type: ignore[index]


class TestNoProjectMode:
    """Tests for task-only mode (no project configured)."""

    @pytest.fixture
    def temp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def manager(self, temp_db):
        from orchestrator.context.memory_manager import MemoryManager

        return MemoryManager(db_path=temp_db, auto_embed=False, auto_index=True)

    def test_store_task_without_project(self, manager):
        task_id = manager.store_task(
            task_description="Global task",
            outcome="Done",
            success=True,
        )
        node = manager.graph_store.get_node(task_id)
        assert node is not None
        assert node.project_id == ""

    def test_global_tasks_visible_without_project_filter(self, manager):
        from orchestrator.context.models.schemas import NodeType

        manager.store_task("Task 1", "Done", True)
        manager.store_task("Task 2", "Done", True)
        tasks = manager.graph_store.query_nodes(node_type=NodeType.TASK)
        assert len(tasks) == 2

    def test_global_context_retrieval(self, manager):
        manager.store_task("Build REST API", "Built endpoints", True)
        context = manager.get_relevant_context("REST API")
        assert "tasks" in context


class TestGraphStoreProjectScoping:
    """Tests for project_id column in graph store."""

    @pytest.fixture
    def temp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def store(self, temp_db):
        from orchestrator.context.store.graph_store import GraphStore

        return GraphStore(temp_db)

    def test_node_has_project_id(self, store):
        from orchestrator.context.models.schemas import Node, NodeType

        node = Node(title="Test", content="Content", project_id="proj123")
        store.add_node(node)
        retrieved = store.get_node(node.id)
        assert retrieved is not None
        assert retrieved.project_id == "proj123"

    def test_query_nodes_by_project_id(self, store):
        from orchestrator.context.models.schemas import Node

        n1 = Node(title="A", content="A content", project_id="proj1")
        n2 = Node(title="B", content="B content", project_id="proj2")
        n3 = Node(title="C", content="C content", project_id="proj1")
        store.add_node(n1)
        store.add_node(n2)
        store.add_node(n3)

        proj1_nodes = store.query_nodes(project_id="proj1")
        proj2_nodes = store.query_nodes(project_id="proj2")
        assert len(proj1_nodes) == 2
        assert len(proj2_nodes) == 1

    def test_update_node_preserves_project_id(self, store):
        from orchestrator.context.models.schemas import Node

        node = Node(title="Original", content="C", project_id="proj1")
        store.add_node(node)
        node.title = "Updated"
        store.update_node(node)
        retrieved = store.get_node(node.id)
        assert retrieved is not None
        assert retrieved.project_id == "proj1"
        assert retrieved.title == "Updated"

    def test_empty_project_id_returns_all(self, store):
        from orchestrator.context.models.schemas import Node

        store.add_node(Node(title="A", project_id="proj1"))
        store.add_node(Node(title="B", project_id=""))
        # No project filter returns all
        all_nodes = store.query_nodes()
        assert len(all_nodes) == 2


class TestProjectNode:
    """Tests for the ProjectNode schema."""

    def test_project_node_creation(self):
        from orchestrator.context.models.schemas import NodeType, ProjectNode

        node = ProjectNode(
            project_path="/tmp/test",
            project_name="test",
            languages=["python"],
            frameworks=["pytest"],
        )
        assert node.node_type == NodeType.PROJECT
        assert node.project_path == "/tmp/test"

    def test_project_node_to_dict(self):
        from orchestrator.context.models.schemas import ProjectNode

        node = ProjectNode(
            project_path="/tmp/test",
            project_name="test",
            languages=["python", "javascript"],
            frameworks=["flask"],
            file_count=42,
        )
        d = node.to_dict()
        assert d["project_path"] == "/tmp/test"
        assert d["project_name"] == "test"
        assert d["languages"] == ["python", "javascript"]
        assert d["file_count"] == 42

    def test_project_node_has_project_id(self):
        from orchestrator.context.models.schemas import ProjectNode

        node = ProjectNode(
            project_path="/tmp/test",
            project_name="test",
            project_id="abc123",
        )
        assert node.project_id == "abc123"
        assert node.to_dict()["project_id"] == "abc123"
