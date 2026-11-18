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

WIKI_ARTICLES = ("Grand_Theft_Auto_VI", "Sick_leave", "Paid_time_off", "Presenteeism")

# The Day-Off Index: US Google searches for these three phrases, compared year over year.
DAY_OFF_INDEX_TERMS = ("call in sick", "sick day", "day off work")
TRENDS_GEO = "US"
# One Trends request per phrase over this whole span, so 2025 and 2026 sit on one 0-100
# scale. Longer than ~9 months, Google answers in weeks (Sunday to Saturday). The span is
# part of the snapshot: a different span rescales every value. It must cover both index
# windows (dbt vars day_off_index_*). Canonical snapshot: 2025-11-01 to 2026-11-15.
TRENDS_SPAN = (dt.date(2025, 11, 1), dt.date(2026, 11, 15))

# Metric 2, GTA V to GTA 6: world productivity between the two launch years, from official
# economic data only. World Bank WDI actuals (world aggregate WLD) and the IMF World Economic
# Outlook's world real GDP growth (WEOWORLD), which carries the year World Bank has not
# published yet.
GTA_V_YEAR = 2013  # GTA V: 17 September 2013
GTA_6_YEAR = 2026  # GTA 6: 19 November 2026
WORLD_BANK_INDICATORS = (
    "SL.GDP.PCAP.EM.KD",  # GDP per person employed, constant 2021 PPP $
    "NY.GDP.PCAP.KD",  # GDP per capita, constant 2015 US$
    "NY.GDP.MKTP.KD",  # GDP, constant 2015 US$ (Metric 3: everything the world made)
    "SP.POP.GROW",  # population growth, annual %
)
IMF_INDICATORS = ("NGDP_RPCH",)  # real GDP growth, annual %
