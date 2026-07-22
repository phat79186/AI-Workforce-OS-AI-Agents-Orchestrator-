"""Base provider interface for AI models and open-source agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderType(str, Enum):
    """Classification of AI providers."""

    LOCAL = "local"
    OPEN_SOURCE = "open_source"
    FREE_TIER = "free_tier"
    PAID = "paid"


@dataclass
class ProviderMetadata:
    """Metadata for AI provider registration."""

    name: str
    provider_type: ProviderType
    cost_per_1k_tokens: float = 0.0
    is_local: bool = True
    capabilities: List[str] = field(default_factory=list)
    context_limit: int = 8192
    priority: int = 100  # Lower number = higher priority
    requires_approval: bool = False
    is_available: bool = True


class BaseProvider:
    """Abstract base class for all model and agent providers."""

    def __init__(self, metadata: ProviderMetadata) -> None:
        self.metadata = metadata

    def check_availability(self) -> bool:
        """Check if the provider is currently available."""
        return self.metadata.is_available

    def execute_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a prompt against the provider."""
        raise NotImplementedError("Subclasses must implement execute_prompt")
