"""Standardized Event Definitions for Event Bus system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Lifecycle event types across orchestrator execution."""

    TASK_CREATED = "TASK_CREATED"
    AGENT_ASSIGNED = "AGENT_ASSIGNED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    TEST_STARTED = "TEST_STARTED"
    TEST_FAILED = "TEST_FAILED"
    TEST_PASSED = "TEST_PASSED"
    DEBUG_STARTED = "DEBUG_STARTED"
    FIX_APPLIED = "FIX_APPLIED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_FAILED = "REVIEW_FAILED"
    TASK_COMPLETED = "TASK_COMPLETED"


@dataclass
class Event:
    """Standardized event record."""

    event_type: EventType
    task_id: str
    agent_role: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
