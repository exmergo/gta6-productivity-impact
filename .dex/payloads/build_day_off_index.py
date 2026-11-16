"""Build .dex/payloads/09-day-off-index.json: the Day-Off Index, redefined.

The Day-Off Index is now the average year-over-year change in US Google searches for three
phrases ("call in sick", "sick day", "day off work"), over a window of Google weeks,
read from one weekly Trends request per phrase spanning both years. Everything from the
Thursday-lift design is removed. Run from the repo root: uv run python .dex/payloads/build_day_off_index.py
"""

import copy
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/09-day-off-index.json"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


# ---------------------------------------------------------------- project vars
project = yaml.safe_load(read("dbt_project.yml"))
project["vars"] = {
    # The Trends request span the index reads (one request per phrase). Must cover both
    # windows. A different span is a different snapshot: Google rescales every value.
    "day_off_index_span_start": "2025-11-01",
    "day_off_index_span_end": "2026-11-15",
    # Pin one pull (batch_id). null = the newest pull for the span.
    # 20261116T185310 is the canonical snapshot behind the 17 Nov 2026 post.
    "day_off_index_batch": "20261116T185310",
    # The current window, in Google weeks (each labelled by its Sunday). Give an end week,
    # or leave it null and give a number of weeks.
    "day_off_index_start_week": "2026-11-01",
    "day_off_index_end_week": "2026-11-08",
    "day_off_index_weeks": 2,
    # The comparison window: the same weeks this many weeks earlier (52 keeps Sundays).
    "day_off_index_weeks_back": 52,
}

# ---------------------------------------------------------------- staging
STG = """-- One row per search phrase per Google week (labelled by its Sunday), from one weekly
-- Trends request per phrase that spans both years, so 2025 and 2026 share one 0-100 scale.
-- Keeps the requests over the configured span (older daily per-year pulls have no span and
-- drop out), and the pinned batch (var day_off_index_batch) or else the newest per phrase.
{%- set batch = var('day_off_index_batch', none) %}
with source as (
    select *
    from {{ source('raw', 'trends_interest') }}
    where span_start = date '{{ var("day_off_index_span_start") }}'
        and span_end = date '{{ var("day_off_index_span_end") }}'
),

chosen as (
    select
        term,
        {% if batch %}'{{ batch }}'{% else %}max(batch_id){% endif %} as batch_id
    from source
    group by term
)

select
    source.request_id,
    source.batch_id,
    source.span_start,
    source.span_end,
    source.geo,
    source.term,
    source.day as week_start,
    cast(source.interest as integer) as interest,
    source.is_partial
from source
inner join chosen
    on source.term = chosen.term
    and source.batch_id = chosen.batch_id
"""

STG_DECL = {
    "model": "stg_trends__weekly",
    "description": "One row per Day-Off Index search phrase per Google week, from one weekly US "
    "Trends request per phrase spanning both years (one 0-100 scale per phrase).",
    "grain": ["term", "week_start"],
    "population": {
        "rule": "Rows of requests over the configured span (vars day_off_index_span_*), from the "
        "pinned batch (var day_off_index_batch) or else each phrase's newest batch. Older daily "
        "per-year pulls carry no span and are excluded."
    },
    "columns": {
        "request_id": {"role": "attribute", "null_rule": "never",
                       "description": "The Trends request: <phrase>-<geo>-<span>-<batch>."},
        "batch_id": {"role": "attribute", "null_rule": "never",
                     "description": "When the pull ran (UTC, YYYYMMDDTHHMMSS)."},
        "span_start": {"role": "attribute", "null_rule": "never",
                       "description": "First day of the request span."},
        "span_end": {"role": "attribute", "null_rule": "never",
                     "description": "Last day of the request span."},
        "geo": {"role": "dimension", "null_rule": "never", "description": "US."},
        "term": {"role": "dimension", "null_rule": "never",
                 "description": "The search phrase: call in sick, sick day or day off work."},
        "week_start": {"role": "time", "null_rule": "never",
                       "description": "The Sunday that starts the Google week."},
        "interest": {"role": "measure", "aggregation": "max", "additivity": "non_additive",
                     "unit": "index (0-100, relative within one phrase's request)",
                     "null_rule": "never",
                     "description": "Relative weekly search interest; 100 is that phrase's peak "
                     "week in the span. Never compare across phrases."},
        "is_partial": {"role": "attribute", "null_rule": "never",
                       "description": "True for the week still in progress when the pull ran."},
    },
    "assumptions": [
        {"decision": "Which Trends rows the index reads", "chosen": "one weekly request per phrase "
         "over the configured span; daily per-year pulls excluded", "evidence": "request",
         "column": "span_start",
         "detail": "user defined the index as one Trends snapshot from 1 Nov 2025 to 15 Nov 2026"},
        {"decision": "Which pull", "chosen": "pinned batch 20261116T185310, else newest",
         "evidence": "request", "column": "batch_id",
         "detail": "user: the canonical snapshot for the post is the one already shown; pulls "
         "differ by 1-2 points because Trends samples"},
    ],
}

# ---------------------------------------------------------------- the breakdown
TERMS = """-- The Day-Off Index breakdown: one row per search phrase, its average weekly search
-- interest over the current window and over the same weeks a year earlier, and the change.
-- The window is configurable (vars day_off_index_*): a start week and an end week, or a
-- start week and a number of weeks. Weeks are Google's, labelled by their Sunday.
{%- set start_week = var('day_off_index_start_week') %}
{%- set end_week = var('day_off_index_end_week', none) %}
{%- set weeks = var('day_off_index_weeks', 2) %}
{%- set weeks_back = var('day_off_index_weeks_back', 52) %}
with params as (
    select
        date '{{ start_week }}' as current_start_week,
        {% if end_week -%}
        date '{{ end_week }}'
        {%- else -%}
        cast(date '{{ start_week }}' + 7 * ({{ weeks }} - 1) as date)
        {%- endif %} as current_end_week
),

windows as (
    select
        current_start_week,
        current_end_week,
        cast(current_start_week - 7 * {{ weeks_back }} as date) as prior_start_week,
        cast(current_end_week - 7 * {{ weeks_back }} as date) as prior_end_week,
        cast((current_end_week - current_start_week) / 7 + 1 as integer) as weeks
    from params
),

phrases as (
    select distinct term, geo, batch_id, span_start, span_end
    from {{ ref('stg_trends__weekly') }}
),

per_phrase as (
    select
        phrases.term,
        phrases.geo,
        phrases.batch_id,
        phrases.span_start,
        phrases.span_end,
        windows.current_start_week,
        windows.current_end_week,
        windows.prior_start_week,
        windows.prior_end_week,
        windows.weeks,
        avg(weekly.interest) filter (
            where weekly.week_start between windows.current_start_week
                and windows.current_end_week and not weekly.is_partial
        ) as current_avg_interest,
        avg(weekly.interest) filter (
            where weekly.week_start between windows.prior_start_week
                and windows.prior_end_week and not weekly.is_partial
        ) as prior_avg_interest,
        count(weekly.week_start) filter (
            where weekly.week_start between windows.current_start_week
                and windows.current_end_week and not weekly.is_partial
        ) as current_weeks_found,
        count(weekly.week_start) filter (
            where weekly.week_start between windows.prior_start_week
                and windows.prior_end_week and not weekly.is_partial
        ) as prior_weeks_found
    from phrases
    cross join windows
    left join {{ ref('stg_trends__weekly') }} as weekly
        on phrases.term = weekly.term
    group by
        phrases.term,
        phrases.geo,
        phrases.batch_id,
        phrases.span_start,
        phrases.span_end,
        windows.current_start_week,
        windows.current_end_week,
        windows.prior_start_week,
        windows.prior_end_week,
        windows.weeks
)

select
    term,
    geo,
    batch_id,
    span_start,
    span_end,
    current_start_week,
    current_end_week,
    prior_start_week,
    prior_end_week,
    weeks,
    current_weeks_found,
    prior_weeks_found,
    current_avg_interest,
    prior_avg_interest,
    case
        when current_weeks_found = weeks
            and prior_weeks_found = weeks
            and prior_avg_interest > 0
            then 100 * (current_avg_interest / prior_avg_interest - 1)
    end as pct_change
from per_phrase
"""

WINDOW_COLS = {
    "current_start_week": {"role": "attribute", "null_rule": "never",
                           "description": "Sunday of the first week of the current window."},
    "current_end_week": {"role": "attribute", "null_rule": "never",
                         "description": "Sunday of the last week of the current window."},
    "prior_start_week": {"role": "attribute", "null_rule": "never",
                         "description": "Sunday of the first comparison week (weeks_back earlier)."},
    "prior_end_week": {"role": "attribute", "null_rule": "never",
                       "description": "Sunday of the last comparison week."},
    "weeks": {"role": "attribute", "null_rule": "never", "unit": "count",
              "description": "Weeks in each window."},
}

TERMS_DECL = {
    "model": "fct_day_off_index_terms",
    "description": "The Day-Off Index breakdown: one row per search phrase, with its average "
    "weekly US search interest over the current window, over the same weeks a year earlier, "
    "and the percent change.",
    "grain": ["term"],
    "population": {
        "rule": "Every phrase in the Trends snapshot the index reads (stg_trends__weekly).",
        "parent": {"model": "stg_trends__weekly", "key": {"term": "term"}},
    },
    "columns": {
        "term": {"role": "key", "null_rule": "never", "description": "The search phrase."},
        "geo": {"role": "dimension", "null_rule": "never", "description": "US."},
        "batch_id": {"role": "attribute", "null_rule": "never",
                     "description": "The Trends pull the values come from."},
        "span_start": {"role": "attribute", "null_rule": "never",
                       "description": "First day of the request span."},
        "span_end": {"role": "attribute", "null_rule": "never",
                     "description": "Last day of the request span."},
        **WINDOW_COLS,
        "current_weeks_found": {"role": "attribute", "null_rule": "never", "unit": "count",
                                "description": "Complete weeks found in the current window."},
        "prior_weeks_found": {"role": "attribute", "null_rule": "never", "unit": "count",
                              "description": "Complete weeks found in the comparison window."},
        "current_avg_interest": {"role": "measure", "aggregation": "max",
                                 "additivity": "non_additive",
                                 "unit": "index (0-100, relative within one phrase's request)",
                                 "null_rule": "NULL when no complete week of the window is loaded",
                                 "description": "Average weekly search interest, current window."},
        "prior_avg_interest": {"role": "measure", "aggregation": "max",
                               "additivity": "non_additive",
                               "unit": "index (0-100, relative within one phrase's request)",
                               "null_rule": "NULL when no complete week of the window is loaded",
                               "description": "Average weekly search interest, same weeks a year earlier."},
        "pct_change": {"role": "measure", "aggregation": "max", "additivity": "non_additive",
                       "unit": "percent",
                       "null_rule": "NULL unless every week of both windows is loaded and complete: unavailable, never zero",
                       "description": "Year-over-year change of the phrase's average weekly "
                       "search interest, in percent (40 = +40%)."},
    },
    "assumptions": [
        {"decision": "What the index compares", "chosen": "average weekly interest over the "
         "current window vs the same weeks 52 weeks earlier, per phrase", "evidence": "request",
         "column": "pct_change",
         "detail": "user: average daily search interest 1-15 Nov 2026 vs 1-15 Nov 2025, weekly is "
         "fine over the 2-week window; configurable start, end and number of weeks"},
        {"decision": "Partial or missing weeks", "chosen": "excluded from the averages; the change "
         "is NULL unless both windows are complete", "evidence": "default", "column": "pct_change",
         "detail": "a week still filling in would understate its average"},
        {"decision": "Week alignment", "chosen": "52 weeks back (364 days), so both windows start on "
         "a Sunday like Google's weeks", "evidence": "default", "column": "prior_start_week",
         "detail": "canonical: 1-14 Nov 2026 vs 2-15 Nov 2025"},
    ],
}

# ---------------------------------------------------------------- the index
INDEX = """-- The Day-Off Index: the average of the three phrases' year-over-year changes, in percent,
-- one row per window. It always carries its breakdown: `breakdown` spells out every phrase's
-- change, so the index is never read without it.
with terms as (
    select
        *,
        cast(current_start_week as varchar) || '/' || cast(current_end_week as varchar)
            as index_window
    from {{ ref('fct_day_off_index_terms') }}
)

select
    index_window,
    min(current_start_week) as current_start_week,
    min(current_end_week) as current_end_week,
    min(prior_start_week) as prior_start_week,
    min(prior_end_week) as prior_end_week,
    min(weeks) as weeks,
    max(batch_id) as batch_id,
    count(*) as phrase_count,
    count(pct_change) as phrases_available,
    case when count(pct_change) = count(*) then avg(pct_change) end as day_off_index,
    string_agg(
        term || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by term
    ) as breakdown
from terms
group by index_window
"""

INDEX_DECL = {
    "model": "fct_day_off_index",
    "description": "The Day-Off Index: the average year-over-year change, in percent, of US Google "
    "searches for call in sick, sick day and day off work over the configured window. One row per "
    "window, always carrying its per-phrase breakdown.",
    "grain": ["index_window"],
    "population": {"rule": "One row for the configured window (vars day_off_index_*)."},
    "columns": {
        "index_window": {"role": "key", "null_rule": "never",
                         "description": "<current_start_week>/<current_end_week>."},
        **WINDOW_COLS,
        "batch_id": {"role": "attribute", "null_rule": "never",
                     "description": "The Trends pull the values come from."},
        "phrase_count": {"role": "attribute", "null_rule": "never", "unit": "count",
                         "description": "Phrases in the index."},
        "phrases_available": {"role": "attribute", "null_rule": "never", "unit": "count",
                              "description": "Phrases whose change is available."},
        "day_off_index": {"role": "measure", "aggregation": "max", "additivity": "non_additive",
                          "unit": "percent",
                          "null_rule": "NULL unless every phrase's change is available: unavailable, never zero",
                          "description": "Average of the phrases' year-over-year changes, in percent "
                          "(50 = searches up 50% on average). Always report with `breakdown`."},
        "breakdown": {"role": "attribute", "null_rule": "never",
                      "description": "Every phrase's change, e.g. 'call in sick +40.4% · day off "
                      "work +73.4% · sick day +36.4%'. Report it with the index, every time."},
    },
    "assumptions": [
        {"decision": "How the phrases combine", "chosen": "plain average of the per-phrase percent "
         "changes", "evidence": "request", "column": "day_off_index",
         "detail": "user: the index is the average of these 3 searches; each phrase is on its own "
         "0-100 scale, so changes are averaged, not interest values"},
        {"decision": "A phrase not yet available", "chosen": "index NULL", "evidence": "default",
         "column": "day_off_index",
         "detail": "an average over fewer phrases would be a different index"},
        {"decision": "Old index columns (study_year, release_day, per-source lifts, source counts)",
         "chosen": "removed; the index is one row per window, no longer per study year",
         "evidence": "request", "column": "study_year",
         "detail": "user: scratch everything of the old Day-Off Index and redefine it"},
        *[{"decision": f"Old index column {c}", "chosen": "removed", "evidence": "request",
           "column": c, "detail": "the Thursday-lift design is retired"}
          for c in ("release_day", "sources_total", "sources_with_lift", "google_trends_lift",
                    "bluesky_lift", "reddit_lift")],
        {"decision": "Index grain", "chosen": "one row per window (index_window), was per study year",
         "evidence": "request", "column": "index_window",
         "detail": "user: one YoY comparison over a configurable window"},
        {"decision": "Breakdown travels with the index", "chosen": "breakdown column on the index row",
         "evidence": "request", "column": "breakdown",
         "detail": "user: the index is always accompanied by its breakdown, never left to be discovered"},
    ],
}

# ---------------------------------------------------------------- edited existing models
int_sql = read("models/intermediate/int_signals__daily.sql")
start = int_sql.index("with trends as (")
end = int_sql.index("bluesky as (")
int_sql = int_sql[:start] + "with " + int_sql[end:]
int_sql = int_sql.replace("select * from trends\nunion all\n", "")
assert "trends" not in int_sql.split("-- A value")[1]

marts = json.loads(read(".dex/payloads/02-marts.json"))
decls = {d["model"]: d for d in marts["declarations"]}
int_decl = copy.deepcopy(decls["int_signals__daily"])
int_decl["columns"]["source"]["description"] = "bluesky, reddit, hacker_news or wikipedia."
int_decl["columns"]["signal"]["description"] = (
    "What is counted, e.g. posts:day_off, posts:day_off_gta, pageviews:grand_theft_auto_vi."
)
int_decl["columns"]["geo"]["description"] = "WORLD."
int_decl["columns"]["signal_date"]["description"] = "UTC day."
int_decl["columns"]["signal_value"]["description"] = (
    "Counts for posts and pageviews. Never add across signals or sources."
)
int_decl["assumptions"] = [a for a in int_decl["assumptions"] if "Trends" not in a["decision"]]
int_decl["assumptions"].append(
    {"decision": "Google Trends signals", "chosen": "removed; Trends now feeds only the Day-Off "
     "Index, weekly, through stg_trends__weekly", "evidence": "request", "column": "source",
     "detail": "user: scratch everything of the old Day-Off Index; the daily per-year Trends pulls "
     "were its input"}
)

dim_sql = read("models/marts/dim_date.sql")
dim_sql = dim_sql.replace(
    """    case cast(date_day - release_day as integer)
        when 0 then 'release'
        when -7 then 'baseline'
    end as comparison_role,
""", "")
assert "comparison_role" not in dim_sql
dim_decl = copy.deepcopy(decls["dim_date"])
del dim_decl["columns"]["comparison_role"]
dim_decl["columns"]["days_from_release"]["description"] = "0 on that year's anchor Thursday."
dim_decl["assumptions"].append(
    {"decision": "Thursday comparison roles", "chosen": "removed", "evidence": "request",
     "column": "comparison_role", "detail": "they tagged the old index's release and baseline Thursdays"}
)

fsd_sql = read("models/marts/fct_signal_daily.sql").replace(
    "    dates.iso_day_of_week,\n    dates.comparison_role\n", "    dates.iso_day_of_week\n")
assert "comparison_role" not in fsd_sql
fsd_decl = copy.deepcopy(decls["fct_signal_daily"])
del fsd_decl["columns"]["comparison_role"]
for col in ("source", "signal", "geo", "signal_date", "signal_value"):
    fsd_decl["columns"][col]["description"] = int_decl["columns"][col]["description"]
fsd_decl["assumptions"].append(
    {"decision": "Thursday comparison roles", "chosen": "removed", "evidence": "request",
     "column": "comparison_role", "detail": "they tagged the old index's release and baseline Thursdays"}
)
fsd_decl["assumptions"].append(
    {"decision": "Google Trends rows and comparison roles", "chosen": "removed", "evidence": "request",
     "column": "source", "detail": "user: scratch the old Day-Off Index; Trends moved to the new index"}
)

# ---------------------------------------------------------------- semantic layer
sig = yaml.safe_load(read("models/marts/semantic/signal_daily.yml"))
sm = sig["semantic_models"][0]
sm["dimensions"] = [d for d in sm["dimensions"] if d["name"] != "comparison_role"]
for d in sm["dimensions"]:
    if d["name"] == "source":
        d["description"] = "bluesky, reddit, hacker_news or wikipedia."
    if d["name"] == "signal":
        d["description"] = "What is counted, e.g. posts:day_off, posts:day_off_gta, pageviews:grand_theft_auto_vi."
    if d["name"] == "geo":
        d["description"] = "WORLD."
    if d["name"] == "signal_date":
        d["description"] = "UTC day."

never = {"config": {"meta": {"dex": {"null_rule": "never"}}}}
DOI_SEM = {
    "version": 2,
    "semantic_models": [
        {
            "name": "fct_day_off_index",
            "description": "The Day-Off Index, one row per window, with its breakdown.",
            "model": "ref('fct_day_off_index')",
            "defaults": {"agg_time_dimension": "current_start_week"},
            "entities": [{"name": "day_off_index_window", "type": "primary", "expr": "index_window", **never}],
            "dimensions": [
                {"name": "breakdown", "type": "categorical",
                 "description": "Every phrase's change. Always report it with the index.", **never},
                {"name": "current_start_week", "type": "time",
                 "type_params": {"time_granularity": "day"}, **never},
                {"name": "current_end_week", "type": "time",
                 "type_params": {"time_granularity": "day"}, **never},
                {"name": "prior_start_week", "type": "time",
                 "type_params": {"time_granularity": "day"}, **never},
                {"name": "prior_end_week", "type": "time",
                 "type_params": {"time_granularity": "day"}, **never},
                {"name": "batch_id", "type": "categorical", **never},
            ],
            "measures": [
                {"name": "day_off_index_measure", "agg": "max", "expr": "day_off_index",
                 "description": "Average YoY change of the phrases, in percent."},
            ],
        },
        {
            "name": "fct_day_off_index_terms",
            "description": "The Day-Off Index breakdown: one row per search phrase.",
            "model": "ref('fct_day_off_index_terms')",
            "defaults": {"agg_time_dimension": "current_start_week"},
            "entities": [{"name": "day_off_index_term", "type": "primary", "expr": "term", **never}],
            "dimensions": [
                {"name": "term", "type": "categorical", "description": "The search phrase.", **never},
                {"name": "current_start_week", "type": "time",
                 "type_params": {"time_granularity": "day"}, **never},
                {"name": "batch_id", "type": "categorical", **never},
            ],
            "measures": [
                {"name": "term_pct_change", "agg": "max", "expr": "pct_change"},
                {"name": "term_current_avg_interest", "agg": "max", "expr": "current_avg_interest"},
                {"name": "term_prior_avg_interest", "agg": "max", "expr": "prior_avg_interest"},
            ],
        },
    ],
}

met = yaml.safe_load(read("models/marts/semantic/metrics.yml"))
KEEP = {"signal_value", "day_off_mentions", "day_off_mentions_gta", "gta_share_of_day_off_talk",
        "gta_wiki_pageviews"}
kept = [m for m in met["metrics"] if m["name"] in KEEP]
assert len(kept) == len(KEEP)
for m in kept:
    if m["name"] == "signal_value":
        m["description"] = ("Daily value of a signal. Always group by signal_day__source and "
                            "signal_day__signal; never add across signals.")
BREAKDOWN_RULE = (" Never report it alone: always with its breakdown (group by "
                  "day_off_index_window__breakdown, or query day_off_index_term_change by "
                  "day_off_index_term__term).")
new_metrics = [
    {"name": "day_off_index", "label": "Day-Off Index",
     "description": "Average year-over-year change, in percent, of US Google searches for call in "
     "sick, sick day and day off work over the configured window (canonical: 1-14 Nov 2026 vs "
     "2-15 Nov 2025). 50 = searches up 50% on average." + BREAKDOWN_RULE,
     "type": "simple", "type_params": {"measure": "day_off_index_measure"}},
    {"name": "day_off_index_term_change", "label": "Day-Off Index, change by phrase",
     "description": "The breakdown: one phrase's year-over-year change in average weekly search "
     "interest, in percent. Group by day_off_index_term__term.",
     "type": "simple", "type_params": {"measure": "term_pct_change"}},
    {"name": "day_off_index_term_current", "label": "Search interest, current window",
     "description": "A phrase's average weekly search interest over the current window (0-100 on "
     "that phrase's own scale). Group by day_off_index_term__term.",
     "type": "simple", "type_params": {"measure": "term_current_avg_interest"}},
    {"name": "day_off_index_term_prior", "label": "Search interest, a year earlier",
     "description": "A phrase's average weekly search interest over the same weeks a year earlier "
     "(0-100 on that phrase's own scale). Group by day_off_index_term__term.",
     "type": "simple", "type_params": {"measure": "term_prior_avg_interest"}},
]
met["metrics"] = new_metrics + kept

TEST = """-- The Day-Off Index never travels without its breakdown: a row with an index has one.
select *
from {{ ref('fct_day_off_index') }}
where day_off_index is not null
    and (breakdown is null or phrases_available <> phrase_count)
"""

def strip_columns(path, drop):
    doc = yaml.safe_load(read(path))
    for model in doc["models"]:
        model["columns"] = [c for c in model.get("columns", []) if c["name"] not in drop]
    return dump(doc)


edits = [
    {"path": "models/marts/dim_date.yml", "kind": "schema_yml",
     "content": strip_columns("models/marts/dim_date.yml", {"comparison_role"})},
    {"path": "models/marts/fct_signal_daily.yml", "kind": "schema_yml",
     "content": strip_columns("models/marts/fct_signal_daily.yml", {"comparison_role"})},
    {"path": "models/marts/fct_day_off_index.yml", "kind": "schema_yml",
     "content": dump({"version": 2, "models": [{"name": "fct_day_off_index"}]})},
    {"path": "dbt_project.yml", "kind": "project_yml", "content": dump(project)},
    # removed: the Thursday-lift design
    {"path": "models/marts/fct_thursday_lift.sql", "kind": "model_sql", "op": "delete"},
    {"path": "models/marts/fct_thursday_lift.yml", "kind": "schema_yml", "op": "delete"},
    {"path": "models/marts/semantic/thursday_lift.yml", "kind": "semantic_yml", "op": "delete"},
    {"path": "models/staging/stg_trends__interest.sql", "kind": "model_sql", "op": "delete"},
    {"path": "models/staging/stg_trends__interest.yml", "kind": "schema_yml", "op": "delete"},
    {"path": "data_tests/assert_control_year_present.sql", "kind": "test_sql", "op": "delete"},
    {"path": "data_tests/assert_no_lift_from_unavailable.sql", "kind": "test_sql", "op": "delete"},
    {"path": "data_tests/assert_thursday_lift_grain.sql", "kind": "test_sql", "op": "delete"},
    # the new index
    {"path": "models/staging/stg_trends__weekly.sql", "kind": "model_sql", "content": STG},
    {"path": "models/marts/fct_day_off_index_terms.sql", "kind": "model_sql", "content": TERMS},
    {"path": "models/marts/fct_day_off_index.sql", "kind": "model_sql", "content": INDEX},
    {"path": "data_tests/assert_day_off_index_has_breakdown.sql", "kind": "test_sql", "content": TEST},
    {"path": "models/marts/semantic/day_off_index.yml", "kind": "semantic_yml", "content": dump(DOI_SEM)},
    # edited
    {"path": "models/intermediate/int_signals__daily.sql", "kind": "model_sql", "content": int_sql},
    {"path": "models/marts/dim_date.sql", "kind": "model_sql", "content": dim_sql},
    {"path": "models/marts/fct_signal_daily.sql", "kind": "model_sql", "content": fsd_sql},
    {"path": "models/marts/semantic/signal_daily.yml", "kind": "semantic_yml", "content": dump(sig)},
    {"path": "models/marts/semantic/metrics.yml", "kind": "semantic_yml", "content": dump(met)},
]
payload = {"edits": edits,
           "declarations": [STG_DECL, TERMS_DECL, INDEX_DECL, int_decl, dim_decl, fsd_decl]}
OUT.write_text(json.dumps(payload, indent=1) + "\n")
print(OUT, len(edits), "edits")
