"""Unit tests for 3-Layer Routers (Agent, Model, Tool) and Provider Registry."""

import pytest
from providers.base_provider import ProviderType
from providers.registry import ProviderRegistry
from orchestrator.routing.agent_router import AgentRouter
from orchestrator.routing.model_router import ModelRouter, RoutingMode
from orchestrator.routing.tool_router import ToolRouter


def test_agent_router_keywords():
    router = AgentRouter()

    res1 = router.route("Implement JWT login feature")
    assert res1.agent_role == "Coding Agent"

    res2 = router.route("Run automated unit tests")
    assert res2.agent_role == "Testing Agent"

    res3 = router.route("Audit code for security vulnerabilities")
    assert res3.agent_role == "Security Review Agent"

    res4 = router.route("Query RAG obsidian vault")
    assert res4.agent_role == "RAG/Knowledge Agent"


def test_model_router_local_first():
    registry = ProviderRegistry()
    router = ModelRouter(registry=registry)

    # Balanced mode
    res = router.route("Fix bug in React component", mode=RoutingMode.BALANCED)
    assert res.provider_type in (ProviderType.LOCAL, ProviderType.OPEN_SOURCE)
    assert res.requires_approval is False


def test_model_router_free_mode_strict():
    registry = ProviderRegistry()
    router = ModelRouter(registry=registry)

    res = router.route("Add login page", mode=RoutingMode.FREE)
    assert res.provider_type in (ProviderType.LOCAL, ProviderType.OPEN_SOURCE)
    assert res.requires_approval is False


def test_tool_router_permissions():
    router = ToolRouter()

    coding_res = router.route("Coding Agent")
    assert "git" in coding_res.allowed_tools
    assert "terminal" in coding_res.allowed_tools

    doc_res = router.route("Documentation Agent")
    assert "obsidian" in doc_res.allowed_tools
