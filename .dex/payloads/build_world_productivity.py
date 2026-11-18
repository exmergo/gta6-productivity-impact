"""Build .dex/payloads/12-world-productivity.json: Metric 2, GTA V to GTA 6.

World productivity between the two launch years (2013 and 2026), from official economic
data only: World Bank WDI world aggregates, and the IMF World Economic Outlook's world real
GDP growth for the year the World Bank has not published yet.
Run from the repo root: uv run python .dex/payloads/build_world_productivity.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/12-world-productivity.json"


def dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


# ---------------------------------------------------------------- sources
sources = yaml.safe_load((ROOT / "models/staging/_sources.yml").read_text())
tables = sources["sources"][0]["tables"]
if not any(t["name"] == "economy_indicators" for t in tables):
    tables.append(
        {
            "name": "economy_indicators",
            "description": (
                "Official economic data, one value per provider, indicator, geography and "
                "year: World Bank WDI world aggregates (WLD) and the IMF World Economic "
                "Outlook world series (WEOWORLD). A year a provider has not published is "
                "absent, never zero."
            ),
        }
    )

# ---------------------------------------------------------------- staging
STG = """-- One row per provider, indicator, geography and year of official economic data.
with source as (
    select * from {{ source('raw', 'economy_indicators') }}
)

select
    provider,
    indicator,
    geo,
    cast(year as integer) as year,
    cast(value as double) as value,
    cast(last_updated as date) as last_updated
from source
"""

STG_YML = {
    "version": 2,
    "models": [
        {
            "name": "stg_economy__indicators",
            "description": "One row per provider, indicator, geography and year: official economic data.",
            "columns": [
                {
                    "name": "provider",
                    "description": "world_bank (WDI) or imf_weo (World Economic Outlook).",
                },
                {
                    "name": "indicator",
                    "description": "The provider's indicator code, e.g. SL.GDP.PCAP.EM.KD or NGDP_RPCH.",
                },
                {"name": "geo", "description": "WLD: the world aggregate."},
                {"name": "year", "description": "Calendar year the value describes."},
                {
                    "name": "value",
                    "description": "The published value, in the indicator's own unit.",
                },
                {
                    "name": "last_updated",
                    "description": "When the World Bank last updated the indicator; NULL for the IMF.",
                },
            ],
        }
    ],
}

# ---------------------------------------------------------------- mart
MART = """-- Metric 2, GTA V to GTA 6: world productivity in every year from GTA V's launch year to
-- GTA 6's, and its real change since GTA V. One row per measure per year.
--   output_per_worker: World Bank GDP per person employed (constant 2021 PPP $).
--   output_per_person: World Bank GDP per capita (constant 2015 US$).
-- A year the World Bank has not published is estimated for output_per_person only: its last
-- published value grown by the IMF's world real GDP growth for each later year, less the
-- World Bank's latest world population growth. output_per_worker stays NULL there
-- (unavailable): no published world employment growth to carry it.
{%- set gta_v = var('gta_v_year', 2013) %}
{%- set gta_6 = var('gta_6_year', 2026) %}
with indicators as (
    select * from {{ ref('stg_economy__indicators') }}
    where geo = 'WLD'
),

measures as (
    select * from (
        values
            ('output_per_worker', 'SL.GDP.PCAP.EM.KD', 'constant 2021 PPP $ per person employed', false),
            ('output_per_person', 'NY.GDP.PCAP.KD', 'constant 2015 US$ per person', true)
    ) as m (measure, source_indicator, unit, carried_by_imf)
),

years as (
    select cast(unnest(range({{ gta_v }}, {{ gta_6 }} + 1)) as integer) as year
),

actuals as (
    select indicator, year, value
    from indicators
    where provider = 'world_bank'
),

last_actual as (
    select indicator, max(year) as last_year, arg_max(value, year) as last_value
    from actuals
    group by indicator
),

gdp_growth as (
    select year, value as gdp_growth_pct
    from indicators
    where provider = 'imf_weo' and indicator = 'NGDP_RPCH'
),

pop_growth as (
    select arg_max(value, year) as pop_growth_pct
    from indicators
    where provider = 'world_bank' and indicator = 'SP.POP.GROW'
),

spine as (
    select
        measures.measure,
        measures.source_indicator,
        measures.unit,
        measures.carried_by_imf,
        years.year,
        actuals.value as actual_value,
        last_actual.last_year,
        last_actual.last_value,
        gdp_growth.gdp_growth_pct,
        pop_growth.pop_growth_pct
    from measures
    cross join years
    cross join pop_growth
    left join actuals
        on actuals.indicator = measures.source_indicator and actuals.year = years.year
    left join last_actual
        on last_actual.indicator = measures.source_indicator
    left join gdp_growth
        on gdp_growth.year = years.year
),

carried as (
    select
        *,
        -- Per-capita growth factor for a year past the last published one; NULL if the IMF
        -- has no growth for it, and a NULL anywhere in the chain keeps the rest NULL.
        case
            when carried_by_imf and year > last_year
                then (1 + gdp_growth_pct / 100) / (1 + pop_growth_pct / 100)
        end as growth_factor
    from spine
),

valued as (
    select
        *,
        case
            when actual_value is not null then actual_value
            when growth_factor is not null and bool_and(growth_factor is not null) over chain
                then last_value * exp(sum(ln(growth_factor)) over chain)
        end as value
    from carried
    window chain as (
        partition by measure, year > last_year
        order by year
        rows between unbounded preceding and current row
    )
),

based as (
    select
        valued.*,
        max(case when year = {{ gta_v }} then value end) over (partition by measure) as gta_v_value,
        max(case when value is not null then year end) over (partition by measure) as latest_year
    from valued
)

select
    md5(measure || '|' || cast(year as varchar)) as world_productivity_key,
    measure,
    year as data_year,
    make_date(year, 1, 1) as year_start,
    case year when {{ gta_v }} then 'GTA V' when {{ gta_6 }} then 'GTA 6' end as launch,
    value,
    unit,
    source_indicator,
    actual_value is null and value is not null as is_estimate,
    year = latest_year as is_latest,
    round(100 * (value / gta_v_value - 1), 1) as pct_change_since_gta_v
from based
"""

MART_DECL = {
    "model": "fct_world_productivity",
    "description": (
        "Metric 2, GTA V to GTA 6: world productivity per year from 2013 to 2026 and its real "
        "change since GTA V's launch year. One row per measure per year."
    ),
    "grain": ["world_productivity_key"],
    "population": {
        "rule": (
            "Every year from var gta_v_year (2013) to var gta_6_year (2026) for both measures, "
            "published or not; an unpublished, unestimated year keeps its row with a NULL value."
        )
    },
    "columns": {
        "world_productivity_key": {
            "role": "key",
            "null_rule": "never",
            "description": "md5 of measure|year.",
        },
        "measure": {
            "role": "dimension",
            "null_rule": "never",
            "description": "output_per_worker or output_per_person.",
        },
        "data_year": {
            "role": "dimension",
            "null_rule": "never",
            "description": "Calendar year the value describes.",
        },
        "year_start": {
            "role": "time",
            "null_rule": "never",
            "description": "1 January of data_year: the time axis.",
        },
        "launch": {
            "role": "dimension",
            "description": "GTA V on 2013, GTA 6 on 2026, NULL in between.",
        },
        "value": {
            "role": "measure",
            "aggregation": "max",
            "additivity": "non_additive",
            "unit": "see unit column",
            "null_rule": "NULL when unpublished and not estimated: unavailable, never zero.",
            "description": "Real output in the measure's unit.",
        },
        "unit": {"role": "attribute", "null_rule": "never", "description": "The value's unit."},
        "source_indicator": {
            "role": "attribute",
            "null_rule": "never",
            "description": "World Bank indicator code.",
        },
        "is_estimate": {
            "role": "attribute",
            "null_rule": "never",
            "description": "True when the value is carried by IMF growth, not published by the World Bank.",
        },
        "is_latest": {
            "role": "attribute",
            "description": "True on the measure's latest year with a value.",
        },
        "pct_change_since_gta_v": {
            "role": "measure",
            "aggregation": "max",
            "additivity": "non_additive",
            "unit": "percent",
            "null_rule": "NULL when the year's value is unavailable.",
            "description": "Real change since GTA V's launch year, in percent.",
        },
    },
    "assumptions": [
        {
            "decision": "Measures of productivity",
            "chosen": "World Bank GDP per person employed and GDP per capita, world aggregate, real",
            "evidence": "request",
            "column": "measure",
            "detail": "user: productivity measured by actual economic indexes (GDP per capita) for the whole world, economic data only",
        },
        {
            "decision": "Years covered",
            "chosen": "2013 to 2026, every year",
            "evidence": "request",
            "column": "data_year",
            "detail": "user: bookended by the GTA V and GTA 6 releases (17 Sep 2013, 19 Nov 2026)",
        },
        {
            "decision": "Years the World Bank has not published",
            "chosen": "per capita carried by IMF WEO world real GDP growth less latest World Bank population growth, flagged is_estimate; per worker left NULL",
            "evidence": "default",
            "column": "value",
            "detail": "the IMF WEO is the standard published source for the current year; no free published world employment growth to carry output per worker",
        },
    ],
}

TEST = """-- Metric 2 is measured from GTA V's launch year: every measure needs its bookend value, or
-- every change since GTA V would read NULL.
select measure
from {{ ref('fct_world_productivity') }}
group by measure
having max(case when data_year = {{ var('gta_v_year', 2013) }} then value end) is null
"""

payload = {
    "edits": [
        {"path": "models/staging/_sources.yml", "kind": "schema_yml", "content": dump(sources)},
        {"path": "models/staging/stg_economy__indicators.sql", "kind": "model_sql", "content": STG},
        {
            "path": "models/staging/stg_economy__indicators.yml",
            "kind": "schema_yml",
            "content": dump(STG_YML),
        },
        {"path": "models/marts/fct_world_productivity.sql", "kind": "model_sql", "content": MART},
        {
            "path": "models/marts/fct_world_productivity.yml",
            "kind": "schema_yml",
            "content": dump({"version": 2, "models": [{"name": "fct_world_productivity"}]}),
        },
        {
            "path": "data_tests/assert_world_productivity_has_gta_v_year.sql",
            "kind": "test_sql",
            "content": TEST,
        },
    ],
    "declarations": [
        {
            "model": "stg_economy__indicators",
            "description": "One row per provider, indicator, geography and year: official economic data.",
            "grain": ["provider", "indicator", "geo", "year"],
            "population": {
                "rule": "Every published value as landed; unpublished years are absent."
            },
            "columns": {
                "provider": {"role": "dimension", "null_rule": "never"},
                "indicator": {"role": "dimension", "null_rule": "never"},
                "geo": {"role": "dimension", "null_rule": "never"},
                "year": {"role": "time", "null_rule": "never", "unit": "years"},
                "value": {
                    "role": "measure",
                    "aggregation": "max",
                    "additivity": "non_additive",
                    "unit": "the indicator's own unit",
                    "null_rule": "never",
                },
                "last_updated": {"role": "attribute"},
            },
            "assumptions": [
                {
                    "decision": "geo flagged as location PII",
                    "chosen": "kept as is",
                    "evidence": "data",
                    "column": "geo",
                    "detail": "its only value is WLD, the world aggregate code; no person or place of a person",
                }
            ],
        },
        MART_DECL,
    ],
}

OUT.write_text(json.dumps(payload, indent=1) + "\n")
print(OUT)
