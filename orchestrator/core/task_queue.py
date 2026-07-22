"""Task Queue managing pending, active, and completed subtasks."""

from __future__ import annotations

import queue
from typing import List, Optional
from orchestrator.core.dependency_graph import TaskNode


class TaskQueue:
    """Thread-safe Task Queue for subtask execution scheduling."""

    def __init__(self) -> None:
        self._queue: queue.Queue[TaskNode] = queue.Queue()
        self._all_tasks: List[TaskNode] = []

    def enqueue(self, task: TaskNode) -> None:
        """Enqueue subtask for execution."""
        self._all_tasks.append(task)
        self._queue.put(task)

    def dequeue(self, timeout: float = 1.0) -> Optional[TaskNode]:
        """Dequeue next available task."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def size(self) -> int:
        """Return count of pending tasks in queue."""
        return self._queue.qsize()

    def list_all(self) -> List[TaskNode]:
        """List all managed tasks."""
        return list(self._all_tasks)
