"""Offline mode detection utilities."""

from __future__ import annotations

import os
import time

import httpx


class OfflineDetector:
    """Detect network availability with cached checks."""

    def __init__(
        self,
        check_interval: int = 60,
        connectivity_url: str | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.check_interval = check_interval
        self.connectivity_url = (
            connectivity_url
            or os.environ.get("CONNECTIVITY_CHECK_URL")
            or "https://httpbin.org/status/200"
        )
        self.timeout_seconds = timeout_seconds
        self._is_offline: bool | None = None
        self._last_check_monotonic: float = 0.0

    def is_offline(self, force_refresh: bool = False) -> bool:
        """Return current offline status using cached connectivity checks."""
        now = time.monotonic()
        cache_is_fresh = (now - self._last_check_monotonic) < self.check_interval

        if force_refresh or self._is_offline is None or not cache_is_fresh:
            self._is_offline = not self._check_connectivity()
            self._last_check_monotonic = now

        return self._is_offline

    def _check_connectivity(self) -> bool:
        """Perform a lightweight online check; only 2xx counts as online."""
        try:
            response = httpx.head(
                self.connectivity_url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
            return 200 <= response.status_code < 300
        except Exception:
            return False
