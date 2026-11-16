"""Hacker News via Algolia: daily hit counts for the same seeds, with and without GTA."""

from __future__ import annotations

import datetime as dt

from gta6_impact.config import SEARCH_SEEDS, WINDOWS
from gta6_impact.http import Http
from gta6_impact.ingest._days import complete_days, epoch

URL = "https://hn.algolia.com/api/v1/search_by_date"
FILTERS = {"any": "", "gta": " gta"}


def run(http: Http, skip: set[tuple] | None = None) -> list[dict]:
    rows = []
    skip = skip or set()
    for window in WINDOWS:
        for day in complete_days(window):
            start, end = epoch(day), epoch(day + dt.timedelta(days=1))
            for seed in SEARCH_SEEDS:
                for filter_name, suffix in FILTERS.items():
                    if (day, seed, filter_name) in skip:
                        continue
                    query = f'"{seed}"{suffix}'
                    try:
                        payload = http.get_json(
                            URL,
                            {
                                "query": query,
                                "tags": "(story,comment)",
                                "numericFilters": f"created_at_i>={start},created_at_i<{end}",
                                "hitsPerPage": 0,
                                "typoTolerance": "false",
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
                            "hits_total": None if payload is None else payload.get("nbHits"),
                            "observed_at": dt.datetime.now(dt.UTC),
                        }
                    )
    return rows
