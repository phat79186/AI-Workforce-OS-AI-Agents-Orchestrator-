"""DAG Dependency Graph for complex multi-step task breakdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional


@dataclass
class TaskNode:
    """Represents a task node in the dependency graph."""

    task_id: str
    description: str
    agent_role: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    output: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)


class DependencyGraph:
    """Directed Acyclic Graph (DAG) for subtask dependency management."""

    def __init__(self) -> None:
        self.nodes: Dict[str, TaskNode] = {}

    def add_task(self, task_id: str, description: str, agent_role: str, dependencies: Optional[List[str]] = None) -> TaskNode:
        """Add a subtask node to the DAG."""
        node = TaskNode(
            task_id=task_id,
            description=description,
            agent_role=agent_role,
            dependencies=dependencies or [],
        )
        self.nodes[task_id] = node
        return node

    def get_ready_tasks(self) -> List[TaskNode]:
        """Return subtasks whose dependencies have all completed."""
        ready = []
        completed_ids = {nid for nid, n in self.nodes.items() if n.status == "completed"}

        for node in self.nodes.values():
            if node.status == "pending":
                if all(dep in completed_ids for dep in node.dependencies):
                    ready.append(node)
        return ready

    def mark_completed(self, task_id: str, output: Optional[str] = None, files_changed: Optional[List[str]] = None) -> None:
        """Mark subtask as completed."""
        if task_id in self.nodes:
            self.nodes[task_id].status = "completed"
            self.nodes[task_id].output = output
            if files_changed:
                self.nodes[task_id].files_changed = files_changed

    def is_all_completed(self) -> bool:
        """Check if all subtasks in DAG are completed."""
        return all(n.status == "completed" for n in self.nodes.values())
