"""Build .dex/payloads/15-world-output.json: Metric 3, everything humanity made while waiting.

World real output (World Bank WDI NY.GDP.MKTP.KD, constant 2015 US$) on every UTC day from
GTA V's release (17 Sep 2013) to the day before GTA 6 (18 Nov 2026), its running total, and
an editorial seed of milestones placed on that running total. Metric 2's models are not
touched: these are new, independent models.
Inputs: .dex/payloads/wait_milestones.csv (the curated milestone list; every date checked
against its source on 2026-11-18, UTC days, primary sources preferred).
Run from the repo root: uv run python .dex/payloads/build_world_output.py
"""

import csv
import io
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/15-world-output.json"
MILESTONES = ROOT / ".dex/payloads/wait_milestones.csv"

GTA_V_DATE = "{{ var('gta_v_date', '2013-09-17') }}"
GTA_6_DATE = "{{ var('gta_6_date', '2026-11-19') }}"


def dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


def model_yml(path: str, name: str) -> str:
    """The model's YAML stub; the declaration renders the rest. Keeps unit tests already
    applied (16-world-output-unit-tests) so a re-plan never drops them."""
    doc = {"version": 2, "models": [{"name": name}]}
    existing = ROOT / path
    if existing.exists():
        tests = (yaml.safe_load(existing.read_text()) or {}).get("unit_tests")
        if tests:
            doc["unit_tests"] = tests
    return dump(doc)


# ---------------------------------------------------------------- project vars
project = yaml.safe_load((ROOT / "dbt_project.yml").read_text())
project["vars"]["gta_v_date"] = "2013-09-17"  # GTA V release, the first day of the wait
project["vars"]["gta_6_date"] = "2026-11-19"  # GTA 6 release (00:00 UTC): the wait ends the day before

# ---------------------------------------------------------------- seed
SEED_COLUMNS = [
    "milestone_id",
    "event_date",
    "date_precision",
    "category",
    "tier",
    "title",
    "chart_label",
    "why",
    "source_url",
]
with MILESTONES.open() as fh:
    rows = list(csv.DictReader(fh))
rows.sort(key=lambda r: (r["event_date"], r["milestone_id"]))
buf = io.StringIO()
writer = csv.DictWriter(buf, fieldnames=SEED_COLUMNS, lineterminator="\n")
writer.writeheader()
for row in rows:
    writer.writerow({c: row[c] for c in SEED_COLUMNS})
SEED = buf.getvalue()
CATEGORIES = sorted({r["category"] for r in rows})
TIERS = ["anchor", "hero", "long"]

SEED_YML = {
    "version": 2,
    "seeds": [
        {
            "name": "wait_milestones",
            "description": (
                "Metric 3: editorially chosen moments between GTA V and GTA 6, one row per "
                "milestone, each dated to a UTC day and carrying one public source. Our picks, "
                "not a ranking."
            ),
            "config": {"column_types": {"event_date": "date"}},
            "columns": [
                {
                    "name": "milestone_id",
                    "description": "Slug, e.g. black_hole_image.",
                    "data_tests": ["unique", "not_null"],
                },
                {
                    "name": "event_date",
                    "description": "UTC day the event happened.",
                    "data_tests": ["not_null"],
                },
                {
                    "name": "date_precision",
                    "description": "day, or month when only the month is certain.",
                    "data_tests": [
                        {"accepted_values": {"arguments": {"values": ["day", "month"]}}}
                    ],
                },
                {
                    "name": "category",
                    "description": "Theme of the milestone; rockstar marks the Rockstar nods.",
                    "data_tests": [{"accepted_values": {"arguments": {"values": CATEGORIES}}}],
                },
                {
                    "name": "tier",
                    "description": "anchor (the two releases), hero (on the chart) or long (site table only).",
                    "data_tests": [{"accepted_values": {"arguments": {"values": TIERS}}}],
                },
                {"name": "title", "description": "What happened, in a sentence."},
                {"name": "chart_label", "description": "Short label for the chart."},
                {"name": "why", "description": "Why it is on the list."},
                {"name": "source_url", "description": "One public source for the date."},
            ],
        }
    ],
}

# ---------------------------------------------------------------- yearly
YEARLY = """-- Metric 3, everything humanity made while waiting for GTA 6: world real output in every
-- year from GTA V's launch year to GTA 6's. One row per year.
-- World Bank WDI GDP (NY.GDP.MKTP.KD, constant 2015 US$, world aggregate). A year the World
-- Bank has not published is its last published value grown by the IMF WEO world real GDP
-- growth for each later year (total output: no population adjustment), flagged is_estimate.
-- A missing IMF year leaves that year and every later one NULL: unavailable, never zero.
with indicators as (
    select * from {{ ref('stg_economy__indicators') }}
    where geo = 'WLD'
),

years as (
    select cast(unnest(range({{ var('gta_v_year', 2013) }}, {{ var('gta_6_year', 2026) }} + 1)) as integer) as year
),

actuals as (
    select year, value
    from indicators
    where provider = 'world_bank' and indicator = 'NY.GDP.MKTP.KD'
),

last_actual as (
    select max(year) as last_year, arg_max(value, year) as last_value
    from actuals
),

gdp_growth as (
    select year, value as gdp_growth_pct
    from indicators
    where provider = 'imf_weo' and indicator = 'NGDP_RPCH'
),

spine as (
    select
        years.year,
        actuals.value as actual_value,
        last_actual.last_year,
        last_actual.last_value,
        gdp_growth.gdp_growth_pct
    from years
    left join last_actual on true
    left join actuals on actuals.year = years.year
    left join gdp_growth on gdp_growth.year = years.year
),

carried as (
    select
        *,
        case when year > last_year then 1 + gdp_growth_pct / 100 end as growth_factor
    from spine
),

valued as (
    select
        *,
        case
            when actual_value is not null then actual_value
            when growth_factor is not null and bool_and(growth_factor is not null) over chain
                then last_value * exp(sum(ln(growth_factor)) over chain)
        end as annual_output
    from carried
    window chain as (
        partition by year > last_year
        order by year
        rows between unbounded preceding and current row
    )
),

sized as (
    select
        *,
        datediff('day', make_date(year, 1, 1), make_date(year + 1, 1, 1)) as days_in_year
    from valued
)

select
    year as data_year,
    annual_output,
    actual_value is null and annual_output is not null as is_estimate,
    days_in_year,
    annual_output / days_in_year as daily_output,
    annual_output / days_in_year / 86400 as output_per_second,
    'NY.GDP.MKTP.KD' as source_indicator
from sized
"""

YEARLY_DECL = {
    "model": "int_world_output__yearly",
    "description": (
        "Metric 3: world real output (GDP, constant 2015 US$) in every year from GTA V's "
        "launch year to GTA 6's, and its even daily and per-second rates. One row per year."
    ),
    "grain": ["data_year"],
    "population": {
        "rule": (
            "Every year from var gta_v_year (2013) to var gta_6_year (2026), published or not; "
            "an unpublished, unestimated year keeps its row with NULL output."
        )
    },
    "columns": {
        "data_year": {"role": "key", "null_rule": "never", "description": "Calendar year."},
        "annual_output": {
            "role": "measure",
            "aggregation": "sum",
            "additivity": "additive",
            "unit": "currency:USD",
            "null_rule": "NULL when unpublished and not estimated: unavailable, never zero.",
            "description": "World real GDP in the year, constant 2015 US$.",
        },
        "is_estimate": {
            "role": "attribute",
            "null_rule": "never",
            "description": "True when carried by IMF growth, not published by the World Bank.",
        },
        "days_in_year": {
            "role": "attribute",
            "null_rule": "never",
            "unit": "days",
            "description": "365, or 366 in a leap year.",
        },
        "daily_output": {
            "role": "measure",
            "aggregation": "sum",
            "additivity": "additive",
            "unit": "currency:USD",
            "null_rule": "NULL when annual_output is.",
            "description": "annual_output / days_in_year: the year spread evenly over its days.",
        },
        "output_per_second": {
            "role": "measure",
            "aggregation": "max",
            "additivity": "non_additive",
            "unit": "currency:USD",
            "null_rule": "NULL when annual_output is.",
            "description": "daily_output / 86400: a rate, the yearly average spread evenly.",
        },
        "source_indicator": {
            "role": "attribute",
            "null_rule": "never",
            "description": "World Bank indicator code.",
        },
    },
    "assumptions": [
        {
            "decision": "What 'everything humanity made' measures",
            "chosen": "World Bank world real GDP, NY.GDP.MKTP.KD, constant 2015 US$",
            "evidence": "request",
            "column": "annual_output",
            "detail": "user: Metric 3 plan, world output between GTA V and GTA 6; same price basis as Metric 2's per-capita series",
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
            "chosen": "last published GDP grown by IMF WEO world real GDP growth, no population adjustment, flagged is_estimate",
            "evidence": "precedent",
            "column": "annual_output",
            "detail": "fct_world_productivity carries the unpublished year with the same IMF chain; total output takes no per-capita adjustment",
        },
        {
            "decision": "Daily output within a year",
            "chosen": "spread evenly over the year's days (365 or 366)",
            "evidence": "default",
            "column": "daily_output",
            "detail": "GDP is published yearly; no seasonality is claimed",
        },
    ],
}

# ---------------------------------------------------------------- daily
DAILY = f"""-- Metric 3, everything humanity made while waiting for GTA 6: one row per UTC day of the
-- wait, from GTA V's release (var gta_v_date) to the day before GTA 6's (var gta_6_date),
-- with that day's world real output and the running total since GTA V.
-- Days are generated here: the wait (2013 to 2026) is wider than the semantic time spine.
-- A day whose year has no output reads NULL, and so does every running total from it on.
with days as (
    select cast(range as date) as output_day
    from range(cast('{GTA_V_DATE}' as date), cast('{GTA_6_DATE}' as date), interval 1 day)
),

yearly as (
    select * from {{{{ ref('int_world_output__yearly') }}}}
),

daily as (
    select
        days.output_day,
        cast(year(days.output_day) as integer) as data_year,
        yearly.daily_output,
        yearly.is_estimate
    from days
    left join yearly on yearly.data_year = year(days.output_day)
)

select
    output_day,
    data_year,
    daily_output,
    is_estimate,
    case
        when bool_and(daily_output is not null) over wait
            then sum(daily_output) over wait
    end as cumulative_output,
    datediff('day', cast('{GTA_V_DATE}' as date), output_day) + 1 as days_since_gta_v,
    datediff('day', output_day, cast('{GTA_6_DATE}' as date)) as days_to_gta_6
from daily
window wait as (order by output_day rows between unbounded preceding and current row)
"""

DAILY_DECL = {
    "model": "fct_world_output_daily",
    "description": (
        "Metric 3, everything humanity made while waiting for GTA 6: world real output on each "
        "UTC day from GTA V's release to the day before GTA 6's, and the running total since "
        "GTA V. One row per day."
    ),
    "grain": ["output_day"],
    "population": {
        "rule": (
            "Every UTC day from var gta_v_date (2013-09-17, GTA V's release) to the day before "
            "var gta_6_date (2026-11-19, GTA 6's release): 4,811 days."
        )
    },
    "columns": {
        "output_day": {"role": "time", "null_rule": "never", "description": "UTC day."},
        "data_year": {
            "role": "dimension",
            "null_rule": "never",
            "description": "Calendar year of output_day.",
        },
        "daily_output": {
            "role": "measure",
            "aggregation": "sum",
            "additivity": "additive",
            "unit": "currency:USD",
            "null_rule": "NULL when the year's output is unavailable.",
            "description": "World real output on the day, constant 2015 US$ (the year spread evenly).",
        },
        "is_estimate": {
            "role": "attribute",
            "description": "True when the day's year is carried by IMF growth.",
        },
        "cumulative_output": {
            "role": "measure",
            "aggregation": "max",
            "additivity": "semi_additive",
            "unit": "currency:USD",
            "null_rule": "NULL from the first day with unavailable output on: never a partial total.",
            "description": "Running total of daily_output from GTA V's release through the day. Never sum it across days.",
        },
        "days_since_gta_v": {
            "role": "attribute",
            "null_rule": "never",
            "unit": "days",
            "description": "1 on GTA V's release day, 4,811 on 18 Nov 2026.",
        },
        "days_to_gta_6": {
            "role": "attribute",
            "null_rule": "never",
            "unit": "days",
            "description": "Days left until GTA 6's release day; 1 on 18 Nov 2026.",
        },
    },
    "assumptions": [
        {
            "decision": "Which days the wait holds",
            "chosen": "2013-09-17 through 2026-11-18, every UTC day",
            "evidence": "request",
            "column": "output_day",
            "detail": "user: bookended by the two releases; GTA 6 unlocks 2026-11-19 00:00 UTC, the site countdown's moment",
        },
        {
            "decision": "What drives the days",
            "chosen": "a range() of days generated in SQL, not metricflow_time_spine",
            "evidence": "default",
            "column": "output_day",
            "detail": "the time spine covers 2025-2027 only; widening it would change a model Metric 1 reads",
        },
        {
            "decision": "Running total across an unavailable day",
            "chosen": "NULL from that day on",
            "evidence": "contract",
            "column": "cumulative_output",
            "detail": "AGENTS.md: a NULL is unavailable, never zero; a total that skipped a year would understate",
        },
    ],
}

# ---------------------------------------------------------------- milestones
MILES = f"""-- Metric 3: each milestone of the wait, placed on the running total of world real output.
-- output_by_then is the running total through the day before the event: "by the time it
-- happened, the world had made $X since GTA V". GTA V's own release day has made nothing yet
-- since GTA V, so it reads 0; any other milestone outside the wait reads NULL.
with milestones as (
    select * from {{{{ ref('wait_milestones') }}}}
),

daily as (
    select * from {{{{ ref('fct_world_output_daily') }}}}
),

wait as (
    select arg_max(cumulative_output, output_day) as wait_output
    from daily
)

select
    milestones.milestone_id,
    milestones.event_date,
    milestones.date_precision,
    milestones.category,
    milestones.tier,
    milestones.title,
    milestones.chart_label,
    milestones.why,
    milestones.source_url,
    case
        when milestones.event_date = cast('{GTA_V_DATE}' as date) then 0
        else daily.cumulative_output
    end as output_by_then,
    output_by_then / wait.wait_output as share_of_wait_output,
    datediff('day', cast('{GTA_V_DATE}' as date), milestones.event_date) as days_since_gta_v,
    datediff('day', milestones.event_date, cast('{GTA_6_DATE}' as date)) as days_to_gta_6
from milestones
left join wait on true
left join daily on daily.output_day = milestones.event_date - 1
"""

MILES_DECL = {
    "model": "fct_wait_milestones",
    "description": (
        "Metric 3: the milestones of the wait between GTA V and GTA 6, each with the world real "
        "output made since GTA V by the day before it. One row per milestone."
    ),
    "grain": ["milestone_id"],
    "population": {
        "rule": "Every milestone in the wait_milestones seed.",
        "parent": {"model": "wait_milestones", "key": {"milestone_id": "milestone_id"}},
    },
    "columns": {
        "milestone_id": {"role": "key", "null_rule": "never"},
        "event_date": {"role": "time", "null_rule": "never", "description": "UTC day of the event."},
        "date_precision": {"role": "attribute", "null_rule": "never"},
        "category": {"role": "dimension", "null_rule": "never"},
        "tier": {
            "role": "dimension",
            "null_rule": "never",
            "description": "anchor, hero (on the chart) or long (site table only).",
        },
        "title": {"role": "dimension", "null_rule": "never"},
        "chart_label": {"role": "dimension", "null_rule": "never"},
        "why": {"role": "attribute"},
        "source_url": {"role": "attribute", "null_rule": "never"},
        "output_by_then": {
            "role": "measure",
            "aggregation": "max",
            "additivity": "semi_additive",
            "unit": "currency:USD",
            "null_rule": "NULL when the event falls outside the wait or the running total is unavailable.",
            "description": "World real output made from GTA V's release through the day before the event, constant 2015 US$.",
        },
        "share_of_wait_output": {
            "role": "measure",
            "aggregation": "max",
            "additivity": "non_additive",
            "unit": "fraction",
            "null_rule": "NULL when output_by_then is.",
            "description": "output_by_then over the whole wait's output: how far through the wait, in output.",
        },
        "days_since_gta_v": {"role": "attribute", "null_rule": "never", "unit": "days"},
        "days_to_gta_6": {"role": "attribute", "null_rule": "never", "unit": "days"},
    },
    "assumptions": [
        {
            "decision": "Which day a milestone's output is read on",
            "chosen": "the running total through the day before the event",
            "evidence": "request",
            "column": "output_by_then",
            "detail": "user: Metric 3 plan; avoids arguing about events late in the UTC day",
        },
        {
            "decision": "GTA V's own release day",
            "chosen": "output_by_then = 0, not NULL",
            "evidence": "request",
            "column": "output_by_then",
            "detail": "user: Metric 3 plan; the day before GTA V lies outside the wait, and nothing has been made since GTA V yet",
        },
    ],
}

# ---------------------------------------------------------------- tests
TEST_COVERS = """-- Metric 3: the wait holds every UTC day from GTA V's release to the day before GTA 6's,
-- once each (4,811 days for 2013-09-17 to 2026-11-18).
select count(*) as days, min(output_day) as first_day, max(output_day) as last_day
from {{ ref('fct_world_output_daily') }}
having count(*) <> datediff('day', cast('{{ var('gta_v_date', '2013-09-17') }}' as date), cast('{{ var('gta_6_date', '2026-11-19') }}' as date))
    or min(output_day) <> cast('{{ var('gta_v_date', '2013-09-17') }}' as date)
    or max(output_day) <> cast('{{ var('gta_6_date', '2026-11-19') }}' as date) - 1
"""

TEST_TOTAL = """-- Metric 3: the last running total is the sum of every day's output, within float rounding,
-- and the running total never falls from one day to the next.
with daily as (
    select
        output_day,
        cumulative_output,
        lag(cumulative_output) over (order by output_day) as previous_output
    from {{ ref('fct_world_output_daily') }}
),

totals as (
    select
        arg_max(cumulative_output, output_day) as last_total,
        (select sum(daily_output) from {{ ref('fct_world_output_daily') }}) as summed
    from daily
)

select 'last total is not the sum of days' as problem, null as output_day
from totals
where last_total is null or abs(last_total - summed) > 1e-6 * summed
union all
select 'running total fell', output_day
from daily
where cumulative_output < previous_output
"""

TEST_INSIDE = """-- Metric 3: every milestone other than GTA V's release falls inside the wait, so its output
-- by then (the day before) exists: from the day after GTA V's release to GTA 6's release day.
select milestone_id, event_date, output_by_then
from {{ ref('fct_wait_milestones') }}
where event_date <> cast('{{ var('gta_v_date', '2013-09-17') }}' as date)
  and (
    event_date <= cast('{{ var('gta_v_date', '2013-09-17') }}' as date)
    or event_date > cast('{{ var('gta_6_date', '2026-11-19') }}' as date)
    or output_by_then is null
  )
"""

PATHS = {
    "int_world_output__yearly": "models/intermediate/int_world_output__yearly.yml",
    "fct_world_output_daily": "models/marts/fct_world_output_daily.yml",
    "fct_wait_milestones": "models/marts/fct_wait_milestones.yml",
}

payload = {
    "edits": [
        {"path": "dbt_project.yml", "kind": "project_yml", "content": dump(project)},
        {"path": "seeds/wait_milestones.csv", "kind": "seed_csv", "content": SEED},
        {"path": "seeds/wait_milestones.yml", "kind": "schema_yml", "content": dump(SEED_YML)},
        {
            "path": "models/intermediate/int_world_output__yearly.sql",
            "kind": "model_sql",
            "content": YEARLY,
        },
        {
            "path": "models/intermediate/int_world_output__yearly.yml",
            "kind": "schema_yml",
            "content": model_yml(PATHS["int_world_output__yearly"], "int_world_output__yearly"),
        },
        {"path": "models/marts/fct_world_output_daily.sql", "kind": "model_sql", "content": DAILY},
        {
            "path": "models/marts/fct_world_output_daily.yml",
            "kind": "schema_yml",
            "content": model_yml(PATHS["fct_world_output_daily"], "fct_world_output_daily"),
        },
        {"path": "models/marts/fct_wait_milestones.sql", "kind": "model_sql", "content": MILES},
        {
            "path": "models/marts/fct_wait_milestones.yml",
            "kind": "schema_yml",
            "content": model_yml(PATHS["fct_wait_milestones"], "fct_wait_milestones"),
        },
        {
            "path": "data_tests/assert_world_output_covers_the_wait.sql",
            "kind": "test_sql",
            "content": TEST_COVERS,
        },
        {
            "path": "data_tests/assert_world_output_running_total.sql",
            "kind": "test_sql",
            "content": TEST_TOTAL,
        },
        {
            "path": "data_tests/assert_wait_milestones_inside_wait.sql",
            "kind": "test_sql",
            "content": TEST_INSIDE,
        },
    ],
    "declarations": [YEARLY_DECL, DAILY_DECL, MILES_DECL],
}

# Send only the files that differ from the tree (and their models' declarations): a plan that
# re-sends an unchanged seed cannot be compared (transform compare: inputs_unsynchronized).
# Model YAML always differs (Dex renders the declarations into it), so it rides along with
# its model's SQL rather than counting as a change on its own.
changed = {
    e["path"]
    for e in payload["edits"]
    if e["kind"] != "schema_yml"
    and (not (ROOT / e["path"]).exists() or (ROOT / e["path"]).read_text() != e["content"])
}
if changed and len(changed) < len([e for e in payload["edits"] if e["kind"] != "schema_yml"]):
    stems = {Path(p).stem for p in changed}
    payload = {
        "edits": [e for e in payload["edits"] if e["path"] in changed or Path(e["path"]).stem in stems],
        "declarations": [d for d in payload["declarations"] if d["model"] in stems],
    }

OUT.write_text(json.dumps(payload, indent=1) + "\n")
print(OUT)
