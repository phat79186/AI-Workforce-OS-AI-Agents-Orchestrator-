"""Integration for public-apis/public-apis directory catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PublicAPIEntry:
    """Entry in the Public APIs catalog."""

    api_name: str
    category: str
    description: str
    auth_type: str  # apiKey, OAuth, None
    cors: str  # yes, no, unknown
    url: str


class PublicAPIsCatalog:
    """Public APIs catalog for querying external API endpoints during microservice planning."""

    def __init__(self) -> None:
        self._entries: List[PublicAPIEntry] = []
        self._seed_catalog()

    def _seed_catalog(self) -> None:
        """Seed public APIs catalog entries."""
        self._entries.append(
            PublicAPIEntry(
                api_name="Face Recognition API",
                category="Security & AI",
                description="Face detection and liveness anti-spoofing API",
                auth_type="apiKey",
                cors="yes",
                url="https://api.public-apis.org/entries?category=AI",
            )
        )
        self._entries.append(
            PublicAPIEntry(
                api_name="GitHub API",
                category="Development",
                description="REST & GraphQL APIs for repository management",
                auth_type="OAuth",
                cors="yes",
                url="https://api.github.com",
            )
        )

    def search_apis(self, category_or_keyword: str) -> List[PublicAPIEntry]:
        """Search Public APIs directory by category or keyword."""
        kw = category_or_keyword.lower()
        return [
            e
            for e in self._entries
            if kw in e.api_name.lower() or kw in e.category.lower() or kw in e.description.lower()
        ]
