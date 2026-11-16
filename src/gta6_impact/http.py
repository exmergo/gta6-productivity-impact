"""One polite HTTP client: a fixed User-Agent, a minimum gap per host, retries with backoff."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from gta6_impact.config import USER_AGENT

RETRY_STATUS = {408, 422, 425, 429, 500, 502, 503, 504}


class Http:
    def __init__(self, min_interval: dict[str, float] | None = None, retries: int = 6) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True
        )
        self._min_interval = min_interval or {}
        self._last: dict[str, float] = {}
        self._retries = retries

    def _wait(self, host: str) -> None:
        gap = self._min_interval.get(host, 0.2)
        elapsed = time.monotonic() - self._last.get(host, 0.0)
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self._last[host] = time.monotonic()

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        host = urlparse(url).netloc
        for attempt in range(self._retries):
            self._wait(host)
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError:
                time.sleep(min(60, 2**attempt))
                continue
            if response.status_code in RETRY_STATUS:
                retry_after = response.headers.get("retry-after")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(min(90, delay))
                continue
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        raise RuntimeError(f"gave up on {url} after {self._retries} attempts")
