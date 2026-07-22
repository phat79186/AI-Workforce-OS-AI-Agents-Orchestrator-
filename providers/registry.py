"""Provider Registry managing local, open-source, free-tier, and paid AI providers."""

from __future__ import annotations

from typing import Dict, List, Optional

from providers.base_provider import BaseProvider, ProviderType
from providers.ollama_provider import OllamaProvider
from providers.openhands_provider import OpenHandsProvider


class ProviderRegistry:
    """Registry maintaining available providers and selection algorithms."""

    def __init__(self) -> None:
        self._providers: Dict[str, BaseProvider] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default local and open-source providers."""
        ollama = OllamaProvider()
        openhands = OpenHandsProvider()

        self.register(ollama)
        self.register(openhands)

    def register(self, provider: BaseProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.metadata.name] = provider

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name."""
        return self._providers.get(name)

    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[BaseProvider]:
        """List providers, optionally filtered by provider_type."""
        if provider_type is None:
            return list(self._providers.values())
        return [p for p in self._providers.values() if p.metadata.provider_type == provider_type]

    def get_preferred_local(self) -> Optional[BaseProvider]:
        """Get highest priority available local/open-source provider."""
        sorted_providers = sorted(
            [p for p in self._providers.values() if p.metadata.is_local],
            key=lambda p: p.metadata.priority,
        )
        for p in sorted_providers:
            if p.check_availability():
                return p
        return sorted_providers[0] if sorted_providers else None
