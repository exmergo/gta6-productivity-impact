"""Study constants: the dates, the phrases, the places we look.

Everything a reader needs to judge the method lives here, in one file.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
MANUAL_DIR = ROOT / "data" / "manual"
WAREHOUSE = ROOT / "warehouse" / "gta6.duckdb"

USER_AGENT = (
    "gta6-productivity-impact/0.1 (open research; "
    "+https://github.com/exmergo/gta6-productivity-impact)"
)

RELEASE_DAY = dt.date(2026, 11, 19)  # Thursday. All days in this study are UTC days.
BASELINE_DAY = dt.date(2026, 11, 12)  # The Thursday before.
CONTROL_RELEASE_DAY = dt.date(2025, 11, 20)  # Same Thursday one year earlier.
CONTROL_BASELINE_DAY = dt.date(2025, 11, 13)


@dataclass(frozen=True)
class Window:
    year: int
    start: dt.date
    end: dt.date  # inclusive


# The study window and its seasonality control, one year apart.
WINDOWS = (
    Window(2026, dt.date(2026, 10, 1), dt.date(2026, 11, 30)),
    Window(2025, dt.date(2025, 10, 2), dt.date(2025, 12, 1)),
)

# Ways people say they are not coming in. Matched case-insensitively on whole words.
DAY_OFF_PHRASES = (
    "day off",
    "days off",
    "time off",
    "pto",
    "sick day",
    "call in sick",
    "calling in sick",
    "called in sick",
    "annual leave",
    "booked off",
)

# Ways people say GTA 6.
GTA_TERMS = ("gta", "gta 6", "gta6", "gta vi", "grand theft auto")

# Search seeds: one query per day-off phrase family, plus a GTA filter. Bluesky search has
# no reliable OR, so we query each seed separately and classify the text ourselves.
SEARCH_SEEDS = ("day off", "time off", "pto", "sick day", "call in sick", "calling in sick")

REDDIT_SUBREDDITS = (
    "GTA6",
    "GTA",
    "gaming",
    "PS5",
    "XboxSeriesX",
    "antiwork",
    "jobs",
    "sysadmin",
    "cscareerquestions",
)

WIKI_ARTICLES = ("Grand_Theft_Auto_VI", "Sick_leave", "Paid_time_off", "Presenteeism")

# Trends rescales each request to its own peak, so "GTA 6" would flatten the day-off terms
# to zero. Each group is its own request.
TRENDS_TERM_GROUPS = {
    "day_off": ("call in sick", "sick day", "PTO", "day off work"),
    "hype": ("GTA 6",),
}
TRENDS_GEOS = ("US", "")  # "" is worldwide.
