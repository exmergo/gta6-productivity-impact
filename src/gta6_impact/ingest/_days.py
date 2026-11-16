from __future__ import annotations

import datetime as dt
from collections.abc import Iterator

from gta6_impact.config import Window


def days(window: Window, until: dt.date | None = None) -> Iterator[dt.date]:
    last = min(window.end, until or window.end)
    day = window.start
    while day <= last:
        yield day
        day += dt.timedelta(days=1)


def complete_days(window: Window) -> Iterator[dt.date]:
    """Only UTC days that have fully ended: a half-day count is not a count."""
    yesterday = dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1)
    yield from days(window, until=yesterday)


def epoch(day: dt.date) -> int:
    return int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.UTC).timestamp())
