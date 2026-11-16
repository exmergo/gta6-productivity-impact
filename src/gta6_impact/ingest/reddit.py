"""Reddit via the Arctic Shift archive: posts and comments that mention time off.

Per (subreddit, kind, seed, week) we page through every match, classify the text in memory
(says day off? mentions GTA?) and keep only ids, timestamps and flags. Every slice we
asked for is recorded in a coverage table, so a slice that failed reads as unavailable,
never as zero.
"""

from __future__ import annotations

import datetime as dt

from gta6_impact.config import REDDIT_SUBREDDITS, SEARCH_SEEDS
from gta6_impact.http import Http
from gta6_impact.text import mentions_day_off, mentions_gta

BASE = "https://arctic-shift.photon-reddit.com/api/{kind}/search"
TEXT_PARAM = {"posts": "query", "comments": "body"}

# Full-text search over months times out upstream, so we read two weeks either side of each
# Thursday pair, a week at a time.
REDDIT_WINDOWS = (
    (dt.date(2026, 11, 1), dt.date(2026, 11, 27)),
    (dt.date(2025, 11, 2), dt.date(2025, 11, 28)),
)


def _weeks(start: dt.date, end: dt.date):
    cursor = start
    while cursor < end:
        nxt = min(cursor + dt.timedelta(days=7), end)
        yield cursor, nxt
        cursor = nxt


def _text(kind: str, item: dict) -> str:
    if kind == "posts":
        return f"{item.get('title') or ''}\n{item.get('selftext') or ''}"
    return item.get("body") or ""


def run(http: Http, max_pages: int = 30) -> tuple[list[dict], list[dict]]:
    items_by_key: dict[tuple[str, str], dict] = {}
    coverage: list[dict] = []
    today = dt.datetime.now(dt.UTC).date()
    for window_start, window_end in REDDIT_WINDOWS:
        window_end = min(window_end, today)
        for start, end in _weeks(window_start, window_end):
            for subreddit in REDDIT_SUBREDDITS:
                for kind in ("posts", "comments"):
                    fields = "id,created_utc,subreddit," + (
                        "title,selftext" if kind == "posts" else "body"
                    )
                    for seed in SEARCH_SEEDS:
                        status, pages, after, matched = "complete", 0, start.isoformat(), 0
                        while True:
                            if pages >= max_pages:
                                status = "capped"
                                break
                            try:
                                payload = http.get_json(
                                    BASE.format(kind=kind),
                                    {
                                        "subreddit": subreddit,
                                        TEXT_PARAM[kind]: seed,
                                        "after": after,
                                        "before": end.isoformat(),
                                        "limit": 100,
                                        "sort": "asc",
                                        "fields": fields,
                                    },
                                )
                            except RuntimeError:
                                status = "failed"
                                break
                            pages += 1
                            batch = (payload or {}).get("data") or []
                            for item in batch:
                                text = _text(kind, item)
                                items_by_key[(kind, item["id"])] = {
                                    "item_id": item["id"],
                                    "kind": kind.rstrip("s"),
                                    "subreddit": item.get("subreddit") or subreddit,
                                    "created_at": dt.datetime.fromtimestamp(
                                        item["created_utc"], dt.UTC
                                    ),
                                    "mentions_day_off": mentions_day_off(text),
                                    "mentions_gta": mentions_gta(text),
                                }
                            matched += len(batch)
                            if len(batch) < 100:
                                break
                            after = str(int(batch[-1]["created_utc"]) + 1)
                        coverage.append(
                            {
                                "subreddit": subreddit,
                                "kind": kind.rstrip("s"),
                                "seed": seed,
                                "slice_start": start,
                                "slice_end": end,
                                "status": status,
                                "pages": pages,
                                "items_matched": matched,
                            }
                        )
    return list(items_by_key.values()), coverage
