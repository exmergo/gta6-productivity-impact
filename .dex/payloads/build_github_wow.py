"""Build .dex/payloads/32-github-week-on-week.json: each GitHub day's count against the same
weekday a week earlier (fct_github_daily.prior_week_count, wow_pct_change), so the card can set
release day against the Thursdays before it from the semantic layer.
Run from the repo root: uv run python .dex/payloads/build_github_wow.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
YML = "models/marts/fct_github_daily.yml"

SQL = """-- Metric 4: GitHub activity per UTC day. One row per day per activity, for every day asked
-- for (release day, the weeks before it and the weeks after it), with the same weekday a week
-- earlier beside it (a date join, not a row offset, so a missing day cannot shift the pairing).
{%- set release_day = var('github_release_day') %}
with daily as (
    select * from {{ ref('stg_github__daily_counts') }}
)

select
    md5(daily.activity || '|' || cast(daily.activity_date as varchar)) as github_day_key,
    daily.activity_date,
    daily.activity,
    case daily.activity
        when 'prs_opened' then 'PRs opened'
        when 'prs_merged' then 'PRs merged'
        when 'commits' then 'Commits'
        else daily.activity
    end as activity_label,
    daily.activity_count,
    daily.is_available,
    dayname(daily.activity_date) as weekday_name,
    daily.activity_date = date '{{ release_day }}' as is_release_day,
    cast(date_diff('day', date '{{ release_day }}', daily.activity_date) as integer)
        as days_from_release,
    daily.observed_at,
    week_before.activity_count as prior_week_count,
    case
        when daily.activity_count is not null and week_before.activity_count > 0
            then 100 * (daily.activity_count / week_before.activity_count - 1)
    end as wow_pct_change
from daily
left join daily as week_before
    on daily.activity = week_before.activity
    and week_before.activity_date = cast(daily.activity_date - 7 as date)
"""


def row(day, count, activity="prs_opened"):
    labels = {"prs_opened": "PRs opened", "commits": "Commits"}
    return {"activity_date": day, "activity": activity, "activity_count": count,
            "is_available": count is not None, "observed_at": "2026-11-20 09:00:00",
            "endpoint": "issues", "query": f"q {activity} {day}"}


STG = "ref('stg_github__daily_counts')"
UNIT_TESTS = [
    {
        "name": "github_week_on_week_pairs_the_same_weekday",
        "description": "Each day is set against the same weekday 7 days earlier, per activity; "
        "the day before or another activity never pairs.",
        "model": "fct_github_daily",
        "overrides": {"vars": {"github_release_day": "2026-11-19"}},
        "given": [{"input": STG, "rows": [
            row("2026-11-12", 1000), row("2026-11-18", 9999), row("2026-11-19", 750),
            row("2026-11-12", 50, "commits")]}],
        "expect": {"rows": [
            {"activity_date": "2026-11-12", "activity": "prs_opened", "prior_week_count": None,
             "wow_pct_change": None},
            {"activity_date": "2026-11-18", "activity": "prs_opened", "prior_week_count": None,
             "wow_pct_change": None},
            {"activity_date": "2026-11-19", "activity": "prs_opened", "prior_week_count": 1000,
             "wow_pct_change": -25.0},
            {"activity_date": "2026-11-12", "activity": "commits", "prior_week_count": None,
             "wow_pct_change": None},
        ]},
    },
    {
        "name": "github_week_on_week_null_when_either_day_is_missing",
        "description": "A NULL count on either day leaves the change NULL, never -100%; a zero "
        "week before has no percent change.",
        "model": "fct_github_daily",
        "overrides": {"vars": {"github_release_day": "2026-11-19"}},
        "given": [{"input": STG, "rows": [
            row("2026-11-05", None), row("2026-11-12", 1000), row("2026-11-19", None),
            row("2026-10-29", 0), row("2026-11-05", 5, "commits"), row("2026-10-29", 0, "commits")]}],
        "expect": {"rows": [
            {"activity_date": "2026-11-05", "activity": "prs_opened", "prior_week_count": 0,
             "wow_pct_change": None},
            {"activity_date": "2026-11-12", "activity": "prs_opened", "prior_week_count": None,
             "wow_pct_change": None},
            {"activity_date": "2026-11-19", "activity": "prs_opened", "prior_week_count": 1000,
             "wow_pct_change": None},
            {"activity_date": "2026-10-29", "activity": "prs_opened", "prior_week_count": None,
             "wow_pct_change": None},
            {"activity_date": "2026-11-05", "activity": "commits", "prior_week_count": 0,
             "wow_pct_change": None},
            {"activity_date": "2026-10-29", "activity": "commits", "prior_week_count": None,
             "wow_pct_change": None},
        ]},
    },
]

doc = yaml.safe_load((ROOT / YML).read_text())
model = doc["models"][0]
cols = {c["name"] for c in model["columns"]}
new_cols = [
    {"name": "prior_week_count", "description": "The same activity on the same weekday a week "
     "earlier. NULL when that day was not counted.",
     "config": {"meta": {"dex": {"role": "measure", "aggregation": "max",
                                 "additivity": "non_additive", "unit": "count",
                                 "null_rule": "NULL when the week-earlier day has no count."}}}},
    {"name": "wow_pct_change", "description": "The day against the same weekday a week earlier, "
     "in percent.",
     "config": {"meta": {"dex": {"role": "measure", "aggregation": "max",
                                 "additivity": "non_additive", "unit": "percent",
                                 "null_rule": "NULL unless both days have a count and the week "
                                 "before is above zero."}}}},
]
model["columns"] += [c for c in new_cols if c["name"] not in cols]
doc["unit_tests"] = UNIT_TESTS
assumption = {
    "decision": "Week-on-week pairing",
    "chosen": "same activity, same weekday 7 calendar days earlier (date join); NULL when either "
    "day is missing",
    "evidence": "request", "column": "wow_pct_change",
    "detail": "user, 20 Nov: add the previous Thursdays as context and highlight the drop; the "
    "headline compares with the Thursday before the same way",
}
dex = model["config"]["meta"]["dex"]
dex["assumptions"] = [a for a in dex["assumptions"] if a.get("column") != "wow_pct_change"]
dex["assumptions"].append(assumption)

NEVER = {"null_rule": "never"}
declaration = {
    "model": "fct_github_daily",
    "description": model["description"],
    "grain": ["activity_date", "activity"],
    "population": {
        "rule": "Every (day, activity) row in staging: 1 Oct 2026 onward, only fully ended UTC "
        "days.",
        "parent": {"model": "stg_github__daily_counts",
                   "key": {"activity_date": "activity_date", "activity": "activity"}},
    },
    "columns": {
        "github_day_key": {"role": "key", **NEVER},
        "activity_date": {"role": "time", **NEVER},
        "activity": {"role": "dimension", **NEVER},
        "activity_label": {"role": "attribute", **NEVER},
        "activity_count": {"role": "measure", "aggregation": "sum", "additivity": "additive",
                           "unit": "count", "null_rule": "NULL when unavailable, never zero. "
                           "Never add across activities."},
        "is_available": {"role": "attribute", **NEVER},
        "weekday_name": {"role": "dimension", **NEVER},
        "is_release_day": {"role": "dimension", **NEVER},
        "days_from_release": {"role": "dimension", **NEVER},
        "observed_at": {"role": "attribute", **NEVER},
        "prior_week_count": new_cols[0]["config"]["meta"]["dex"],
        "wow_pct_change": new_cols[1]["config"]["meta"]["dex"],
    },
    "assumptions": dex["assumptions"],
}

edits = [
    {"path": "models/marts/fct_github_daily.sql", "kind": "model_sql", "content": SQL},
    {"path": YML, "kind": "schema_yml",
     "content": yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)},
]
(ROOT / ".dex/payloads/32-github-week-on-week.json").write_text(
    json.dumps({"edits": edits, "declarations": [declaration]}, indent=1, ensure_ascii=False)
    + "\n")
print("ok")
