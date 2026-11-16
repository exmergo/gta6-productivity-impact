"""Google Trends via trendspy: relative daily interest, one request per (geo, year window).

Trends rescales every request to its own 0-100, so values are only comparable inside one
pull. Both Thursdays of a year sit in the same request by construction. When Google
rate-limits us, drop a manual CSV export in data/manual/trends/ (see docs/sources.md).
"""

from __future__ import annotations

import datetime as dt
import time

from gta6_impact.config import TRENDS_GEOS, TRENDS_TERM_GROUPS, WINDOWS


def run(retries: int = 4) -> list[dict]:
    from trendspy import Trends

    client = Trends()
    rows = []
    for window in WINDOWS:
        end = min(window.end, dt.datetime.now(dt.UTC).date())
        timeframe = f"{window.start.isoformat()} {end.isoformat()}"
        for (group, terms), geo in (
            (item, geo) for item in TRENDS_TERM_GROUPS.items() for geo in TRENDS_GEOS
        ):
            frame = None
            for attempt in range(retries):
                try:
                    frame = client.interest_over_time(list(terms), timeframe=timeframe, geo=geo)
                    break
                except Exception:  # noqa: BLE001 - trendspy raises plain exceptions on 429
                    time.sleep(30 * (attempt + 1))
            if frame is None:
                continue
            stamp = f"{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%S}"
            request_id = f"{group}-{geo or 'WORLD'}-{window.year}-{stamp}"
            for ts, record in frame.iterrows():
                for term in terms:
                    if term not in record:
                        continue
                    rows.append(
                        {
                            "request_id": request_id,
                            "term_group": group,
                            "geo": geo or "WORLD",
                            "term": term,
                            "day": ts.date(),
                            "interest": int(record[term]),
                            "is_partial": bool(record.get("isPartial", False)),
                        }
                    )
            time.sleep(5)
    return rows
