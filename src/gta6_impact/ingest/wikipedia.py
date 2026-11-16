"""Wikipedia pageviews (users only, all access), daily. The per-article API has no hourly."""

from __future__ import annotations

import datetime as dt

from gta6_impact.config import WIKI_ARTICLES, WINDOWS
from gta6_impact.http import Http

URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/"
    "all-access/user/{article}/{granularity}/{start}/{end}"
)


def run(http: Http) -> list[dict]:
    rows = []
    for window in WINDOWS:
        last = min(window.end, dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1))
        start = window.start.strftime("%Y%m%d") + "00"
        end = last.strftime("%Y%m%d") + "23"
        jobs = [(a, "daily") for a in WIKI_ARTICLES]
        for article, granularity in jobs:
            url = URL.format(article=article, granularity=granularity, start=start, end=end)
            payload = http.get_json(url) or {"items": []}
            for item in payload["items"]:
                ts = dt.datetime.strptime(item["timestamp"], "%Y%m%d%H").replace(tzinfo=dt.UTC)
                rows.append(
                    {
                        "article": article,
                        "granularity": granularity,
                        "ts": ts,
                        "views": int(item["views"]),
                    }
                )
    return rows
