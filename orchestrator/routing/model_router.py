"""Layer 2: Model Router (THINK WITH WHAT?) - Selects AI Provider following local-first priority."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from providers.base_provider import BaseProvider, ProviderType
from providers.registry import ProviderRegistry


class RoutingMode(str, Enum):
    """Cost & resource routing modes."""

    FREE = "free"  # Strictly Local / Open-Source / Free APIs only
    LOCAL = "local"  # Strictly local/self-hosted (Ollama/llama.cpp)
    BALANCED = "balanced"  # Default: Local/Free first, prompt for Paid fallback
    PREMIUM = "premium"  # Allows high-tier paid models for complex tasks


@dataclass
class ModelRouteResult:
    """Selection result from Model Router."""

    provider: BaseProvider
    provider_type: ProviderType
    mode: RoutingMode
    requires_approval: bool
    rationale: str


class ModelRouter:
    """Intelligent Model Router implementing Local-First priority hierarchy:

    LOCAL / SELF-HOSTED -> OPEN-SOURCE AGENTS -> FREE TIER -> PAID API
    """

    def __init__(self, registry: Optional[ProviderRegistry] = None) -> None:
        self.registry = registry or ProviderRegistry()

    def route(
        self,
        task_description: str,
        mode: RoutingMode = RoutingMode.BALANCED,
        complexity_score: int = 1,
    ) -> ModelRouteResult:
        """Select best AI provider based on routing mode, priority hierarchy, and task complexity."""
        # Level 1: Local / Self-Hosted (Ollama / Local LLM)
        locals_list = self.registry.list_providers(ProviderType.LOCAL)
        for provider in locals_list:
            if provider.check_availability():
                return ModelRouteResult(
                    provider=provider,
                    provider_type=ProviderType.LOCAL,
                    mode=mode,
                    requires_approval=False,
                    rationale="Selected Level 1: Local/Self-hosted provider (Zero cost)",
                )

        # Level 2: Open-Source Agents (OpenHands, CLI tools)
        os_list = self.registry.list_providers(ProviderType.OPEN_SOURCE)
        for provider in os_list:
            if provider.check_availability():
                return ModelRouteResult(
                    provider=provider,
                    provider_type=ProviderType.OPEN_SOURCE,
                    mode=mode,
                    requires_approval=False,
                    rationale="Selected Level 2: Open-source agent provider",
                )

        # Level 3: Free Tier
        free_list = self.registry.list_providers(ProviderType.FREE_TIER)
        for provider in free_list:
            if provider.check_availability():
                return ModelRouteResult(
                    provider=provider,
                    provider_type=ProviderType.FREE_TIER,
                    mode=mode,
                    requires_approval=False,
                    rationale="Selected Level 3: Free-tier provider",
                )

        # If in --free or --local mode and no free resource available
        if mode in (RoutingMode.FREE, RoutingMode.LOCAL):
            preferred = self.registry.get_preferred_local()
            if preferred:
                return ModelRouteResult(
                    provider=preferred,
                    provider_type=preferred.metadata.provider_type,
                    mode=mode,
                    requires_approval=False,
                    rationale=f"Selected fallback local provider for {mode.value} mode",
                )
            raise RuntimeError(
                f"Task cannot be completed reliably using available free/local resources in --{mode.value} mode."
            )

        # Level 4: Paid API (Fallback requiring user approval)
        paid_list = self.registry.list_providers(ProviderType.PAID)
        if paid_list:
            provider = paid_list[0]
            return ModelRouteResult(
                provider=provider,
                provider_type=ProviderType.PAID,
                mode=mode,
                requires_approval=True,
                rationale="Level 1-3 unavailable. Fallback to Paid API requires user confirmation.",
            )

        # Final default fallback
        default_provider = self.registry.get_preferred_local()
        if not default_provider:
            raise RuntimeError("No AI providers available in registry.")

        return ModelRouteResult(
            provider=default_provider,
            provider_type=default_provider.metadata.provider_type,
            mode=mode,
            requires_approval=False,
            rationale="Selected default registry fallback provider",
        )
