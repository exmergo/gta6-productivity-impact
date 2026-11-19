"""GitHub: how many pull requests were opened and merged, and how many commits were made, per
UTC day, from the GitHub Search API.

One request per (activity, day), reading only `total_count` (per_page=1). No repository, user,
title or URL is stored: only the count, whether GitHub said the result was incomplete, and when
we asked. A token in GITHUB_TOKEN (the Actions one is enough) raises the search quota from 10
to 30 calls a minute; it is never required.
"""

from __future__ import annotations

import datetime as dt
import os

from gta6_impact.config import GITHUB_ACTIVITIES, GITHUB_SPAN, Window
from gta6_impact.http import Http
from gta6_impact.ingest._days import complete_days

URL = "https://api.github.com/search/{endpoint}"
# A search that times out answers with incomplete_results; ask again before giving up.
ATTEMPTS = 3


def token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def query(activity: str, day: dt.date) -> tuple[str, str]:
    """The endpoint and search query covering exactly one UTC day."""
    endpoint, template = GITHUB_ACTIVITIES[activity]
    start = f"{day.isoformat()}T00:00:00Z"
    end = f"{day.isoformat()}T23:59:59Z"
    return endpoint, template.format(start=start, end=end)


def run(http: Http, skip: set[tuple] | None = None) -> list[dict]:
    rows = []
    skip = skip or set()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token():
        headers["Authorization"] = f"Bearer {token()}"
    window = Window(GITHUB_SPAN[0].year, *GITHUB_SPAN)
    for day in complete_days(window):
        for activity in GITHUB_ACTIVITIES:
            if (day, activity) in skip:
                continue
            endpoint, q = query(activity, day)
            payload = None
            for _ in range(ATTEMPTS):
                try:
                    payload = http.get_json(
                        URL.format(endpoint=endpoint), {"q": q, "per_page": 1}, headers=headers
                    )
                except Exception:  # noqa: BLE001 - unavailable, never zero
                    payload = None
                if payload is not None and not payload.get("incomplete_results"):
                    break
            rows.append(
                {
                    "day": day,
                    "activity": activity,
                    "endpoint": endpoint,
                    "query": q,
                    "total_count": None if payload is None else payload.get("total_count"),
                    "incomplete_results": True
                    if payload is None
                    else bool(payload.get("incomplete_results")),
                    "observed_at": dt.datetime.now(dt.UTC),
                }
            )
    return rows
