"""Integration for public-apis/public-apis — now fetches and parses the REAL catalog.

`PublicAPIsCatalog.load()` downloads the real, current `README.md` from
`raw.githubusercontent.com/public-apis/public-apis/master/README.md` (~1,700
real API entries across ~50 categories as of writing) and parses its real
markdown tables — nothing here is hand-written data anymore. Requires
network access to `raw.githubusercontent.com`; if that's unavailable, `load()`
raises `PublicAPIsFetchError` rather than silently falling back to fake data.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

README_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"

# Matches a real markdown table row like:
# | [Name](https://example.com) | Some description | `apiKey` | Yes | No |
_ROW_RE = re.compile(
    r"^\|\s*\[(?P<name>[^\]]+)\]\((?P<url>[^)]+)\)\s*\|\s*(?P<description>[^|]*)\|"
    r"\s*(?P<auth>[^|]*)\|\s*(?P<https>[^|]*)\|\s*(?P<cors>[^|]*)\|"
)
_CATEGORY_RE = re.compile(r"^###\s+(.+)$")


class PublicAPIsFetchError(RuntimeError):
    """Raised when the real public-apis README can't be downloaded or parsed."""


@dataclass
class PublicAPIEntry:
    """A single real entry parsed from the public-apis/public-apis README table."""

    name: str
    description: str
    category: str
    url: str
    auth: str
    https: bool
    cors: str


class PublicAPIsCatalog:
    """Fetches and searches the REAL public-apis/public-apis catalog (~1,700 entries)."""

    def __init__(self) -> None:
        self.source_repo = "public-apis/public-apis"
        self._entries: List[PublicAPIEntry] = []
        self._loaded = False

    def load(self, timeout: int = 15) -> int:
        """Download and parse the real README from GitHub. Returns the number of entries parsed.

        Raises `PublicAPIsFetchError` if the network request fails — callers
        should handle this rather than silently getting an empty/fake result.
        """
        try:
            req = urllib.request.Request(README_URL, headers={"User-Agent": "ai-workforce-os"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise PublicAPIsFetchError(f"Could not fetch {README_URL}: {e}") from e

        entries: List[PublicAPIEntry] = []
        current_category = "Uncategorized"
        for line in text.splitlines():
            cat_match = _CATEGORY_RE.match(line.strip())
            if cat_match:
                current_category = cat_match.group(1).strip()
                continue
            row_match = _ROW_RE.match(line.strip())
            if row_match:
                auth = row_match.group("auth").strip().strip("`")
                https = row_match.group("https").strip().lower().startswith("yes")
                entries.append(
                    PublicAPIEntry(
                        name=row_match.group("name").strip(),
                        description=row_match.group("description").strip(),
                        category=current_category,
                        url=row_match.group("url").strip(),
                        auth=auth or "No",
                        https=https,
                        cors=row_match.group("cors").strip(),
                    )
                )

        if not entries:
            raise PublicAPIsFetchError(
                "Fetched the README but parsed 0 entries — the upstream table format may have changed."
            )

        self._entries = entries
        self._loaded = True
        return len(self._entries)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def search_apis(self, query: str, category: Optional[str] = None, limit: int = 20) -> List[PublicAPIEntry]:
        """Search the real loaded catalog by substring match on name/description (and optional category)."""
        self._ensure_loaded()
        q = query.lower().strip()
        results = []
        for entry in self._entries:
            if category and entry.category.lower() != category.lower():
                continue
            if q and q not in entry.name.lower() and q not in entry.description.lower():
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def list_categories(self) -> List[str]:
        """Return the real list of categories found in the loaded catalog."""
        self._ensure_loaded()
        seen: List[str] = []
        for entry in self._entries:
            if entry.category not in seen:
                seen.append(entry.category)
        return seen

    def __len__(self) -> int:
        return len(self._entries)
