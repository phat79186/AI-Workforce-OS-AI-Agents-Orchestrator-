"""In-memory & persistent Event Store for event history logging."""

from __future__ import annotations

from typing import List, Optional
from orchestrator.events.events import Event, EventType


class EventStore:
    """Historical event logger for auditability and metrics."""

    def __init__(self) -> None:
        self._history: List[Event] = []

    def record(self, event: Event) -> None:
        """Record event into history."""
        self._history.append(event)

    def get_events(self, task_id: Optional[str] = None, event_type: Optional[EventType] = None) -> List[Event]:
        """Query recorded events."""
        res = self._history
        if task_id:
            res = [e for e in res if e.task_id == task_id]
        if event_type:
            res = [e for e in res if e.event_type == event_type]
        return list(res)
