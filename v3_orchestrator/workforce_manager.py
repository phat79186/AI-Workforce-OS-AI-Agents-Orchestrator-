"""v3.0 Workforce Manager orchestrating Layer 1 Core Kernel, Layer 2 Domains, Layer 3 Shared Knowledge, and Layer 4 AI Workforce."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from workforce import AIWorkforceRegistry, AIEmployee
from shared_knowledge import KnowledgeBridge
from orchestrator.routing import AgentRouter, ModelRouter, ToolRouter
from orchestrator.events import EventBus, EventStore, Event, EventType


class V3WorkforceManager:
    """Master AI OS v3.0 Workforce Manager."""

    def __init__(self, vault_path: Optional[str] = None) -> None:
        self.workforce = AIWorkforceRegistry()
        self.knowledge_bridge = KnowledgeBridge(vault_path=vault_path)
        self.agent_router = AgentRouter()
        self.model_router = ModelRouter()
        self.tool_router = ToolRouter()
        self.event_bus = EventBus()
        self.event_store = EventStore()

        # Connect event store to event bus
        for et in EventType:
            self.event_bus.subscribe(et, self.event_store.record)

    def execute_task(self, task_description: str, required_skills: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute task by recruiting AI employee, querying shared knowledge, and routing execution."""
        # 1. Recruit AI Employee from Layer 4 AI Workforce
        skills = required_skills or ["Python", "Debugging"]
        employee = self.workforce.recruit(*skills)

        # 2. Retrieve shared knowledge from Layer 3 Shared Knowledge Bridge
        context_docs = self.knowledge_bridge.retrieve_context_for_agent(task_description)

        # 3. Route via Layer 1 Kernel Routers
        agent_route = self.agent_router.route(task_description)
        model_route = self.model_router.route(task_description)
        tool_route = self.tool_router.route(agent_route.agent_role)

        # 4. Emit Events via Layer 1 Event Bus
        task_id = f"TASK-V3-{len(self.event_store.get_events()) + 1}"
        self.event_bus.publish(Event(event_type=EventType.TASK_CREATED, task_id=task_id, payload={"prompt": task_description}))
        self.event_bus.publish(Event(event_type=EventType.AGENT_ASSIGNED, task_id=task_id, agent_role=employee.name if employee else agent_route.agent_role))

        return {
            "task_id": task_id,
            "assigned_employee": employee.name if employee else "DefaultAgent",
            "employee_role": employee.role if employee else agent_route.agent_role,
            "provider": model_route.provider.metadata.name,
            "allowed_tools": tool_route.allowed_tools,
            "retrieved_context_count": len(context_docs),
            "status": "completed",
        }
