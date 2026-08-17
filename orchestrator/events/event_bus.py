"""Pub-Sub Event Bus for decoupled system monitoring and state updates."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List
from orchestrator.events.events import Event, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], None]


class EventBus:
    """Synchronous / Asynchronous Event Bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all registered subscribers."""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                # A broken subscriber must not break the publish loop for others,
                # but the failure is still logged so it doesn't vanish silently.
                logger.exception(
                    "Event handler %r raised while handling %s", handler, event.event_type
                )
