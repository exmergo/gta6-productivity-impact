"""Product Hunt: how many products launched, and how many comments they got on launch day, per
Pacific day (Product Hunt's own day), from the Product Hunt API v2 (GraphQL).

Two landings per day:

- `producthunt_days`: the API's `totalCount` of posts in the day, how many we listed, and whether
  every launch's comments were read in full.
- `producthunt`: one row per launch: its numeric id, when it launched, whether Product Hunt
  featured it, its top-level comments written during its launch day, and its comment counts as
  of the pull.

Only counts, ids, timestamps and flags are stored: no names, taglines, comment text, usernames or
URLs. A token in PRODUCTHUNT_TOKEN (a Product Hunt developer token) is required.

Why top-level comments: comment timestamps are what make two launch days comparable (a launch a
week old has had a week more to collect comments), and the API refuses a query that also asks
for every reply's timestamp at a day's volume (its complexity cap is 500,000).
"""

from __future__ import annotations

import datetime as dt
import os
import time
from zoneinfo import ZoneInfo

import httpx

from gta6_impact.config import PRODUCTHUNT_DAYS, USER_AGENT

URL = "https://api.producthunt.com/v2/api/graphql"
PACIFIC = ZoneInfo("America/Los_Angeles")
PAGE = 20  # the API's largest page
# Each call costs 100 of 6,250 points per 15 minutes. Keep a margin for other callers.
RESERVE = 200

POSTS = """
query($after: DateTime!, $before: DateTime!, $cursor: String) {
  posts(postedAfter: $after, postedBefore: $before, first: 20, after: $cursor, order: NEWEST) {
    totalCount
    pageInfo { hasNextPage endCursor }
    edges { node {
      id createdAt featuredAt commentsCount
      comments(first: 20) {
        totalCount pageInfo { hasNextPage endCursor } edges { node { createdAt } }
      }
    } }
  }
}
"""

MORE_COMMENTS = """
query($id: ID!, $cursor: String) {
  post(id: $id) {
    comments(first: 20, after: $cursor) {
      pageInfo { hasNextPage endCursor } edges { node { createdAt } }
    }
  }
}
"""


def token() -> str | None:
    return os.environ.get("PRODUCTHUNT_TOKEN") or None


def bounds(day: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """A Pacific day as a UTC interval [start, end)."""
    start = dt.datetime(day.year, day.month, day.day, tzinfo=PACIFIC)
    end = start + dt.timedelta(days=1)
    # DST: add a day on the wall clock, not 24 hours.
    end = dt.datetime(end.year, end.month, end.day, tzinfo=PACIFIC)
    return start.astimezone(dt.UTC), end.astimezone(dt.UTC)


def ts(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


class Client:
    def __init__(self, bearer: str) -> None:
        self._http = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=60,
        )

    def query(self, text: str, variables: dict) -> dict:
        for attempt in range(8):
            try:
                response = self._http.post(URL, json={"query": text, "variables": variables})
            except httpx.TransportError:
                time.sleep(min(60, 2**attempt))
                continue
            remaining = response.headers.get("x-rate-limit-remaining")
            reset = response.headers.get("x-rate-limit-reset")
            if response.status_code == 429 or (
                remaining is not None and int(remaining) < RESERVE
            ):
                time.sleep(int(reset or 60) + 2)
                if response.status_code == 429:
                    continue
            if response.status_code >= 500:
                time.sleep(min(60, 2**attempt))
                continue
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise RuntimeError(str(payload["errors"])[:300])
            return payload["data"]
        raise RuntimeError("Product Hunt API: gave up after 8 attempts")


def count_in(edges: list[dict], start: dt.datetime, end: dt.datetime) -> int:
    return sum(1 for e in edges if start <= ts(e["node"]["createdAt"]) < end)


def one_day(client: Client, day: dt.date) -> tuple[dict, list[dict]]:
    start, end = bounds(day)
    # postedBefore is inclusive: stop one second short of the next day.
    window = {
        "after": start.isoformat().replace("+00:00", "Z"),
        "before": (end - dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
    }
    launches: list[dict] = []
    total = None
    cursor = None
    while True:
        data = client.query(POSTS, {**window, "cursor": cursor})["posts"]
        total = data["totalCount"]
        for edge in data["edges"]:
            node = edge["node"]
            comments = node["comments"]
            on_day = count_in(comments["edges"], start, end)
            more = comments["pageInfo"]["hasNextPage"]
            after = comments["pageInfo"]["endCursor"]
            while more:
                page = client.query(MORE_COMMENTS, {"id": node["id"], "cursor": after})
                page = page["post"]["comments"]
                on_day += count_in(page["edges"], start, end)
                more = page["pageInfo"]["hasNextPage"]
                after = page["pageInfo"]["endCursor"]
            launches.append(
                {
                    "day": day,
                    "post_id": str(node["id"]),
                    "launched_at": ts(node["createdAt"]),
                    "is_featured": node["featuredAt"] is not None,
                    "comments_launch_day": on_day,
                    "comments_top_level": comments["totalCount"],
                    "comments_total": node["commentsCount"],
                    "observed_at": dt.datetime.now(dt.UTC),
                }
            )
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    ids = {row["post_id"] for row in launches}
    summary = {
        "day": day,
        "day_start": start,
        "day_end": end,
        "launches_total": total,
        "launches_listed": len(ids),
        "observed_at": dt.datetime.now(dt.UTC),
    }
    return summary, launches


def days_to_ask(skip: set[dt.date]) -> list[dt.date]:
    """The configured Pacific days that have ended and are not yet settled."""
    now = dt.datetime.now(dt.UTC)
    return [d for d in PRODUCTHUNT_DAYS if bounds(d)[1] <= now and d not in skip]


def run(skip: set[dt.date] | None = None, on_day=None) -> tuple[list[dict], list[dict]]:
    """Every ended day not in skip. on_day(summary, launches) lands each day as it finishes,
    so a long backfill keeps what it has if it stops."""
    days = days_to_ask(skip or set())
    if not days:
        return [], []
    bearer = token()
    if not bearer:
        raise RuntimeError("PRODUCTHUNT_TOKEN is not set")
    client = Client(bearer)
    summaries, launches = [], []
    for day in days:
        summary, rows = one_day(client, day)
        if on_day:
            on_day(summary, rows)
        summaries.append(summary)
        launches.extend(rows)
    return summaries, launches
