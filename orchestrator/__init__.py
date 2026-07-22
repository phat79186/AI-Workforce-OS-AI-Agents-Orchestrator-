"""
AI Agent Orchestrator

Core orchestration system for coordinating multiple AI coding assistants.

Package structure:
    orchestrator/
    ├── adapters/        AI agent adapters (Claude, Codex, Gemini, etc.)
    ├── core/            Engine, workflow, task management, exceptions
    ├── resilience/      Fallback, retry, circuit breaker, offline detection
    ├── observability/   Metrics, health checks, structured logging
    ├── security_module/ Input validation, rate limiting, secrets, audit
    ├── infra/           Caching, async execution, config management
    ├── cli/             Interactive REPL shell
    ├── config/          YAML configuration
    └── ui/              Web UI backend
"""

# Re-exports so ``from orchestrator import Orchestrator`` still works.
from .cli import ConversationHistory, InteractiveShell  # noqa: F401
from .core import Orchestrator, TaskManager, WorkflowEngine, WorkflowStep  # noqa: F401
from .resilience import FallbackManager, OfflineDetector  # noqa: F401

__all__ = [
    "Orchestrator",
    "WorkflowEngine",
    "WorkflowStep",
    "TaskManager",
    "FallbackManager",
    "OfflineDetector",
    "InteractiveShell",
    "ConversationHistory",
]
