"""Build .dex/payloads/16-world-output-unit-tests.json: unit tests for Metric 3's yearly model.

They prove the IMF chain for years the World Bank has not published (total output, no
population adjustment), that a missing IMF year leaves that year and every later one NULL,
leap years (366 days), the geo, provider and indicator filters, and the per-day and
per-second rates. The scaffold (review 76) is an empty stub; the fixtures are authored here. Mutants m03
(inner join to the one-row last_actual) and m08 (year >= last_year, which only reaches a
published year) are equivalent: no fixture can tell them apart (review 80).
Run from the repo root: uv run python .dex/payloads/build_world_output_unit_tests.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/16-world-output-unit-tests.json"
YML = "models/intermediate/int_world_output__yearly.yml"
GDP = "NY.GDP.MKTP.KD"
YEARS = range(2013, 2027)  # the model's default bookends: GTA V (2013) to GTA 6 (2026)
LEAP = {2016, 2020, 2024}


def wb(year, value, indicator=GDP, geo="WLD"):
    return {"provider": "world_bank", "indicator": indicator, "geo": geo, "year": year, "value": value}


def imf(year, value, indicator="NGDP_RPCH"):
    return {"provider": "imf_weo", "indicator": indicator, "geo": "WLD", "year": year, "value": value}


def days(year):
    return 366 if year in LEAP else 365


# Published to 2024: 10 a day in every year up to 2023, 20 a day in 2024 (a leap year).
PUBLISHED = {y: 10.0 * days(y) for y in range(2013, 2024)} | {2024: 7320.0}
BASE = [wb(y, v) for y, v in PUBLISHED.items()] + [
    wb(2025, 999.0, geo="USA"),  # not the world: must be ignored
    wb(2025, 999.0, indicator="NY.GDP.PCAP.KD"),  # per capita, not total output
    imf(2024, 9.0),  # growth for a published year: must not enter the chain
    imf(2026, 100.0),
    {"provider": "world_bank", "indicator": "NGDP_RPCH", "geo": "WLD", "year": 2025, "value": 50.0},
    {"provider": "imf_weo", "indicator": GDP, "geo": "WLD", "year": 2025, "value": 1.0},
]


def expect(values: dict, estimates: set) -> list[dict]:
    rows = []
    for year in YEARS:
        value = values.get(year)
        n = days(year)
        rows.append(
            {
                "data_year": year,
                "annual_output": value,
                "is_estimate": year in estimates,
                "days_in_year": n,
                "daily_output": None if value is None else value / n,
                "output_per_second": None if value is None else value / n / 86400,
            }
        )
    return rows


doc = yaml.safe_load((ROOT / YML).read_text())
doc["unit_tests"] = [
    {
        "name": "world_output_carries_unpublished_years_by_imf_growth",
        "description": (
            "2025 = 7320 x (1 - 50%) = 3660 and 2026 = 3660 x (1 + 100%) = 7320, both estimates, "
            "with no population adjustment: the chain compounds every year (two factors, so a "
            "sum of logs cannot pass as a max); leap years have 366 days; other geographies, providers and "
            "indicators are ignored."
        ),
        "model": "int_world_output__yearly",
        "given": [{"input": "ref('stg_economy__indicators')", "rows": BASE + [imf(2025, -50.0)]}],
        "expect": {"rows": expect(PUBLISHED | {2025: 3660.0, 2026: 7320.0}, {2025, 2026})},
    },
    {
        "name": "world_output_missing_imf_year_breaks_the_chain",
        "description": (
            "With no IMF growth for 2025, 2025 and 2026 are both NULL (unavailable), though 2026 "
            "has a growth figure: a gap is never skipped over, and never read as zero."
        ),
        "model": "int_world_output__yearly",
        "given": [{"input": "ref('stg_economy__indicators')", "rows": BASE}],
        "expect": {"rows": expect(PUBLISHED, set())},
    },
]

payload = {
    "edits": [
        {
            "path": YML,
            "kind": "schema_yml",
            "content": yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True),
        }
    ]
}
OUT.write_text(json.dumps(payload, indent=1) + "\n")
print(OUT)
