"""Bluesky: how many public posts a day say they are taking time off, with and without GTA.

We read `hitsTotal` from app.bsky.feed.searchPosts bounded to one UTC day. One request per
(seed, filter, day). No post text, handle or URI is stored: only the count.
"""

from __future__ import annotations

import datetime as dt

from gta6_impact.config import SEARCH_SEEDS, WINDOWS
from gta6_impact.http import Http
from gta6_impact.ingest._days import complete_days

URL = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"
FILTERS = {"any": "", "gta": " gta"}


def run(http: Http, skip: set[tuple] | None = None) -> list[dict]:
    rows = []
    skip = skip or set()
    for window in WINDOWS:
        for day in complete_days(window):
            for seed in SEARCH_SEEDS:
                for filter_name, suffix in FILTERS.items():
                    if (day, seed, filter_name) in skip:
                        continue
                    query = f'"{seed}"{suffix}'
                    try:
                        payload = http.get_json(
                            URL,
                            {
                                "q": query,
                                "since": f"{day.isoformat()}T00:00:00Z",
                                "until": f"{day.isoformat()}T23:59:59.999Z",
                                "limit": 1,
                                "sort": "latest",
                            },
                        )
                    except Exception:  # noqa: BLE001 - unavailable, never zero
                        payload = None
                    rows.append(
                        {
                            "day": day,
                            "seed": seed,
                            "gta_filter": filter_name,
                            "query": query,
                            "hits_total": None if payload is None else payload.get("hitsTotal"),
                            "observed_at": dt.datetime.now(dt.UTC),
                        }
                    )
    return rows
