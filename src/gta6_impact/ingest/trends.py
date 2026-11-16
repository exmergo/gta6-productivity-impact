"""Google Trends via trendspy: weekly US search interest for the Day-Off Index phrases.

Trends rescales every request to its own 0-100, so two values only compare inside one
request. Each phrase gets one request over the whole TRENDS_SPAN, which holds both the
2025 and the 2026 window, so the year-over-year comparison reads one scale. Over a span
longer than ~9 months Google returns weeks (Sunday start), not days.

Every row carries the span and the batch it came from: the span is part of the snapshot
(a different span rescales every value), and staging can pin one batch.

When Google rate-limits us, drop a manual export in data/manual/trends/ (see
docs/sources.md).
"""

from __future__ import annotations

import datetime as dt
import time

from gta6_impact.config import DAY_OFF_INDEX_TERMS, TRENDS_GEO, TRENDS_SPAN


def run(retries: int = 4) -> list[dict]:
    from trendspy import Trends

    client = Trends()
    start, end = TRENDS_SPAN
    timeframe = f"{start.isoformat()} {end.isoformat()}"
    batch = f"{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%S}"
    rows = []
    for term in DAY_OFF_INDEX_TERMS:
        frame = None
        for attempt in range(retries):
            try:
                frame = client.interest_over_time([term], timeframe=timeframe, geo=TRENDS_GEO)
                break
            except Exception:  # noqa: BLE001 - trendspy raises plain exceptions on 429
                time.sleep(30 * (attempt + 1))
        if frame is None:
            raise RuntimeError(f"Google Trends refused {term!r} after {retries} tries")
        request_id = f"{term.replace(' ', '_')}-{TRENDS_GEO}-{start}_{end}-{batch}"
        for ts, record in frame.iterrows():
            rows.append(
                {
                    "request_id": request_id,
                    "batch_id": batch,
                    "span_start": start,
                    "span_end": end,
                    "geo": TRENDS_GEO,
                    "term": term,
                    "day": ts.date(),
                    "interest": int(record[term]),
                    "is_partial": bool(record.get("isPartial", False)),
                }
            )
        time.sleep(5)
    return rows
