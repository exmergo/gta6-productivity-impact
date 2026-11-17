"""Build .dex/payloads/14-world-productivity-unit-tests.json: unit tests for Metric 2.

`dex transform test --scaffold` refuses fct_world_productivity (its {% set %} block makes the
rendered SELECT dbt's), so the tests are authored here, as in 10-day-off-index-unit-tests.
They prove the IMF chain for years the World Bank has not published, that a missing IMF year
leaves the value NULL (never skipped), the geo filter, and the change since GTA V.
Run from the repo root: uv run python .dex/payloads/build_world_productivity_unit_tests.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/14-world-productivity-unit-tests.json"
YML = "models/marts/fct_world_productivity.yml"


def wb(indicator, year, value, geo="WLD"):
    return {
        "provider": "world_bank",
        "indicator": indicator,
        "geo": geo,
        "year": year,
        "value": value,
    }


def imf(year, value):
    return {
        "provider": "imf_weo",
        "indicator": "NGDP_RPCH",
        "geo": "WLD",
        "year": year,
        "value": value,
    }


PERSON, WORKER, POP = "NY.GDP.PCAP.KD", "SL.GDP.PCAP.EM.KD", "SP.POP.GROW"
YEARS = range(2013, 2027)  # the model's default bookends: GTA V (2013) to GTA 6 (2026)
LAUNCH = {2013: "GTA V", 2026: "GTA 6"}

BASE = (
    [wb(PERSON, 2013, 100.0)]
    + [wb(PERSON, y, 110.0) for y in range(2014, 2025)]  # published to 2024
    + [
        wb(PERSON, 2013, 999.0, geo="USA"),  # not the world: must be ignored
        wb(POP, 2023, 5.0),  # older population growth: the latest (2024) must win
        wb(POP, 2024, 1.0),
        imf(2024, 9.0),  # growth for a published year: must not enter the chain
        imf(2026, 2.0),
        # Same codes under the other provider: neither counts.
        {
            "provider": "world_bank",
            "indicator": "NGDP_RPCH",
            "geo": "WLD",
            "year": 2025,
            "value": 50.0,
        },
        {"provider": "imf_weo", "indicator": PERSON, "geo": "WLD", "year": 2025, "value": 1.0},
    ]
)


def expect(person, worker):
    """person/worker: {year: (is_estimate, is_latest, pct)}; unlisted years are unavailable."""
    rows = []
    for measure, values in (("output_per_person", person), ("output_per_worker", worker)):
        for year in YEARS:
            is_estimate, is_latest, pct = values.get(year, (False, False, None))
            rows.append(
                {
                    "measure": measure,
                    "data_year": year,
                    "launch": LAUNCH.get(year),
                    "is_estimate": is_estimate,
                    "is_latest": is_latest,
                    "pct_change_since_gta_v": pct,
                }
            )
    return rows


PUBLISHED = {2013: (False, False, 0.0)} | {y: (False, False, 10.0) for y in range(2014, 2025)}

doc = yaml.safe_load((ROOT / YML).read_text())
doc["unit_tests"] = [
    {
        "name": "world_productivity_carries_unpublished_years_by_imf_growth",
        "description": (
            "2025 = 110 x 1.03/1.01 (+12.2% on 2013), 2026 = 2025 x 1.02/1.01 (+13.3%), both "
            "estimates; the latest population growth (1.0) is used; output per worker stops at "
            "its last published year; other geographies and providers are ignored."
        ),
        "model": "fct_world_productivity",
        "given": [
            {
                "input": "ref('stg_economy__indicators')",
                "rows": BASE + [wb(WORKER, 2013, 50.0), imf(2025, 3.0)],
            }
        ],
        "expect": {
            "rows": expect(
                PUBLISHED | {2025: (True, False, 12.2), 2026: (True, True, 13.3)},
                {2013: (False, True, 0.0)},
            )
        },
    },
    {
        "name": "world_productivity_missing_imf_year_breaks_the_chain",
        "description": (
            "With no IMF growth for 2025, 2025 and 2026 are both NULL (unavailable): a gap is "
            "never skipped over, and the latest year is 2024. A measure with nothing published "
            "keeps every year, all unavailable."
        ),
        "model": "fct_world_productivity",
        "given": [{"input": "ref('stg_economy__indicators')", "rows": BASE}],
        "expect": {
            "rows": expect(
                PUBLISHED | {2024: (False, True, 10.0)},
                {y: (False, None, None) for y in YEARS},
            )
        },
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
