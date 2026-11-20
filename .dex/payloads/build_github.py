"""Build .dex/payloads/25-github.json: Metric 4, did GitHub go quiet on GTA 6's release day?

GitHub Search API counts per UTC day (PRs opened, PRs merged, commits) land in raw.github_daily_counts.
Release day is compared with the average of the same weekday in the weeks before it.
Run from the repo root: uv run python .dex/payloads/build_github.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/25-github.json"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


# ---------------------------------------------------------------- project vars
project = yaml.safe_load(read("dbt_project.yml"))
project["vars"]["github_release_day"] = "2026-11-19"
# The baseline: the same weekday in each of this many weeks before release day, as a median.
# 1 = the Thursday before (12 Nov 2026): GitHub grows week on week, so the nearest week is the
# like-for-like control.
project["vars"]["github_baseline_weeks"] = 1

# ---------------------------------------------------------------- source
sources = yaml.safe_load(read("models/staging/_sources.yml"))
tables = sources["sources"][0]["tables"]
if not any(t["name"] == "github_daily_counts" for t in tables):
    tables.append(
        {
            "name": "github_daily_counts",
            "description": (
                "GitHub Search API total_count for one activity (prs_opened, prs_merged, commits) "
                "bounded to one UTC day, one call each. total_count is NULL when the call failed; "
                "incomplete_results is true when GitHub's search timed out (or the call failed). "
                "No repository, user, title or URL is stored."
            ),
        }
    )

STG = """-- One row per UTC day per GitHub activity, from one GitHub Search API call each (Metric 4).
-- activity_count is NULL when the call failed or GitHub flagged the result incomplete:
-- unavailable, never zero.
select
    cast(day as date) as activity_date,
    activity,
    endpoint,
    query,
    case
        when total_count is not null and not coalesce(incomplete_results, true)
            then cast(total_count as bigint)
    end as activity_count,
    total_count is not null and not coalesce(incomplete_results, true) as is_available,
    observed_at
from {{ source('raw', 'github_daily_counts') }}
"""

DAILY = """-- Metric 4: GitHub activity per UTC day. One row per day per activity, for every day asked
-- for (release day, the weeks before it and the weeks after it).
{%- set release_day = var('github_release_day') %}
select
    md5(activity || '|' || cast(activity_date as varchar)) as github_day_key,
    activity_date,
    activity,
    case activity
        when 'prs_opened' then 'PRs opened'
        when 'prs_merged' then 'PRs merged'
        when 'commits' then 'Commits'
        else activity
    end as activity_label,
    activity_count,
    is_available,
    dayname(activity_date) as weekday_name,
    activity_date = date '{{ release_day }}' as is_release_day,
    cast(date_diff('day', date '{{ release_day }}', activity_date) as integer)
        as days_from_release,
    observed_at
from {{ ref('stg_github__daily_counts') }}
"""

ACTIVITIES = """-- Metric 4 breakdown: one row per GitHub activity. Release day's count against the median of
-- the same weekday in each of the weeks before it (vars github_release_day and
-- github_baseline_weeks; canonical: Thu 19 Nov 2026 vs the Thursday before, 12 Nov). A median,
-- so one bulk-import spike in the commit counts cannot move a longer baseline.
{%- set release_day = var('github_release_day') %}
{%- set weeks = var('github_baseline_weeks', 1) %}
with params as (
    select
        date '{{ release_day }}' as release_day,
        cast({{ weeks }} as integer) as baseline_weeks,
        cast(date '{{ release_day }}' - 7 * {{ weeks }} as date) as baseline_start,
        cast(date '{{ release_day }}' - 7 as date) as baseline_end
),

activities as (
    select distinct activity, activity_label
    from {{ ref('fct_github_daily') }}
),

per_activity as (
    select
        activities.activity,
        activities.activity_label,
        params.release_day,
        params.baseline_weeks,
        params.baseline_start,
        params.baseline_end,
        max(daily.activity_count) filter (
            where daily.activity_date = params.release_day
        ) as release_day_count,
        median(daily.activity_count) filter (
            where daily.activity_date between params.baseline_start and params.baseline_end
                and dayofweek(daily.activity_date) = dayofweek(params.release_day)
        ) as baseline_count,
        count(daily.activity_count) filter (
            where daily.activity_date between params.baseline_start and params.baseline_end
                and dayofweek(daily.activity_date) = dayofweek(params.release_day)
        ) as baseline_days_found
    from activities
    cross join params
    left join {{ ref('fct_github_daily') }} as daily
        on activities.activity = daily.activity
    group by
        activities.activity,
        activities.activity_label,
        params.release_day,
        params.baseline_weeks,
        params.baseline_start,
        params.baseline_end
)

select
    activity,
    activity_label,
    release_day,
    baseline_weeks,
    baseline_start,
    baseline_end,
    baseline_days_found,
    baseline_count,
    release_day_count,
    case
        when release_day_count is not null
            and baseline_days_found = baseline_weeks
            and baseline_count > 0
            then 100 * (release_day_count / baseline_count - 1)
    end as pct_change
from per_activity
"""

INDEX = """-- Metric 4 headline: the average of the activities' release-day changes, in percent, one row
-- per release day. It always carries its breakdown: `breakdown` spells out every activity's
-- change, so the headline is never read without it.
select
    cast(release_day as varchar) as release_day_key,
    min(release_day) as release_day,
    min(baseline_start) as baseline_start,
    min(baseline_end) as baseline_end,
    min(baseline_weeks) as baseline_weeks,
    count(*) as activities_total,
    count(pct_change) as activities_available,
    case when count(pct_change) = count(*) then avg(pct_change) end as github_release_day_change,
    string_agg(
        activity_label || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by activity desc
    ) as breakdown
from {{ ref('fct_github_release_day_activities') }}
group by release_day
"""

TEST = """-- The GitHub release-day change never travels without its breakdown.
select *
from {{ ref('fct_github_release_day') }}
where github_release_day_change is not null
    and (breakdown is null or activities_available <> activities_total)
"""


def model_yml(name: str, description: str, columns: dict[str, str]) -> str:
    return dump(
        {
            "version": 2,
            "models": [
                {
                    "name": name,
                    "description": description,
                    "columns": [{"name": c, "description": d} for c, d in columns.items()],
                }
            ],
        }
    )


STG_COLS = {
    "activity_date": "UTC day the count covers.",
    "activity": "prs_opened, prs_merged or commits.",
    "endpoint": "GitHub search endpoint asked (issues or commits).",
    "query": "The exact search query, bounded to the UTC day.",
    "activity_count": "GitHub's total_count. NULL when unavailable, never zero.",
    "is_available": "True when the call answered with a complete count.",
    "observed_at": "When we asked (UTC).",
}
DAILY_COLS = {
    "github_day_key": "md5 of activity|day.",
    "activity_date": "UTC day.",
    "activity": "prs_opened, prs_merged or commits.",
    "activity_label": "PRs opened, PRs merged or Commits.",
    "activity_count": "How many on the day. NULL when unavailable, never zero.",
    "is_available": "True when the day's count is complete.",
    "weekday_name": "Day of the week.",
    "is_release_day": "True on GTA 6's release day (var github_release_day).",
    "days_from_release": "Days after release day (negative before it).",
    "observed_at": "When the count was asked for (UTC).",
}
ACT_COLS = {
    "activity": "prs_opened, prs_merged or commits.",
    "activity_label": "PRs opened, PRs merged or Commits.",
    "release_day": "GTA 6's release day (var github_release_day).",
    "baseline_weeks": "How many same weekdays before release day form the baseline.",
    "baseline_start": "First baseline day.",
    "baseline_end": "Last baseline day (a week before release day).",
    "baseline_days_found": "Baseline days with a count.",
    "baseline_count": "Median count over the baseline days (the day itself when there is one).",
    "release_day_count": "Count on release day. NULL until the day is over and counted.",
    "pct_change": "Release day against the baseline average, in percent.",
}
INDEX_COLS = {
    "release_day_key": "Release day as text: the row's key.",
    "release_day": "GTA 6's release day.",
    "baseline_start": "First baseline day.",
    "baseline_end": "Last baseline day.",
    "baseline_weeks": "Baseline days (same weekday, weeks before).",
    "activities_total": "Activities in the breakdown.",
    "activities_available": "Activities with a change.",
    "github_release_day_change": "Average of the activities' changes, in percent.",
    "breakdown": "Every activity's change. Always report it with the headline.",
}

edits = [
    {"path": "dbt_project.yml", "kind": "project_yml", "content": dump(project)},
    {"path": "models/staging/_sources.yml", "kind": "schema_yml", "content": dump(sources)},
    {"path": "models/staging/stg_github__daily_counts.sql", "kind": "model_sql", "content": STG},
    {
        "path": "models/staging/stg_github__daily_counts.yml",
        "kind": "schema_yml",
        "content": model_yml(
            "stg_github__daily_counts",
            "GitHub Search API daily counts, one row per UTC day per activity.",
            STG_COLS,
        ),
    },
    {"path": "models/marts/fct_github_daily.sql", "kind": "model_sql", "content": DAILY},
    {
        "path": "models/marts/fct_github_daily.yml",
        "kind": "schema_yml",
        "content": model_yml(
            "fct_github_daily",
            "Metric 4: GitHub activity per UTC day, one row per day per activity.",
            DAILY_COLS,
        ),
    },
    {
        "path": "models/marts/fct_github_release_day_activities.sql",
        "kind": "model_sql",
        "content": ACTIVITIES,
    },
    {
        "path": "models/marts/fct_github_release_day_activities.yml",
        "kind": "schema_yml",
        "content": model_yml(
            "fct_github_release_day_activities",
            "Metric 4 breakdown: release day against the same weekday in the weeks before, "
            "one row per activity.",
            ACT_COLS,
        ),
    },
    {"path": "models/marts/fct_github_release_day.sql", "kind": "model_sql", "content": INDEX},
    {
        "path": "models/marts/fct_github_release_day.yml",
        "kind": "schema_yml",
        "content": model_yml(
            "fct_github_release_day",
            "Metric 4 headline: average release-day change across activities, one row per "
            "release day, with its breakdown.",
            INDEX_COLS,
        ),
    },
    {
        "path": "data_tests/assert_github_release_day_has_breakdown.sql",
        "kind": "test_sql",
        "content": TEST,
    },
]

NEVER = {"null_rule": "never"}
declarations = [
    {
        "model": "stg_github__daily_counts",
        "description": "GitHub Search API daily counts, one row per UTC day per activity.",
        "grain": ["activity_date", "activity"],
        "population": {"rule": "Every (day, activity) the ingester asked for; newest pull wins."},
        "columns": {
            "activity_date": {"role": "time", **NEVER},
            "activity": {"role": "dimension", **NEVER},
            "endpoint": {"role": "attribute", **NEVER},
            "query": {"role": "attribute", **NEVER},
            "activity_count": {
                "role": "measure",
                "aggregation": "sum",
                "additivity": "additive",
                "unit": "count",
                "null_rule": "NULL when the call failed or GitHub flagged it incomplete.",
            },
            "is_available": {"role": "attribute", **NEVER},
            "observed_at": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "A search GitHub flags incomplete_results",
                "chosen": "count NULL (unavailable)",
                "evidence": "contract",
                "column": "activity_count",
                "detail": "AGENTS.md: a NULL is unavailable, never zero; a timed-out search "
                "is a lower bound, not the count",
            }
        ],
    },
    {
        "model": "fct_github_daily",
        "description": "Metric 4: GitHub activity per UTC day, one row per day per activity.",
        "grain": ["activity_date", "activity"],
        "population": {
            "rule": "Every (day, activity) row in staging: 1 Oct 2026 onward, only fully ended "
            "UTC days.",
            "parent": {
                "model": "stg_github__daily_counts",
                "key": {"activity_date": "activity_date", "activity": "activity"},
            },
        },
        "columns": {
            "github_day_key": {"role": "key", **NEVER, "description": "md5 of activity|day."},
            "activity_date": {"role": "time", **NEVER},
            "activity": {"role": "dimension", **NEVER},
            "activity_label": {"role": "attribute", **NEVER},
            "activity_count": {
                "role": "measure",
                "aggregation": "sum",
                "additivity": "additive",
                "unit": "count",
                "null_rule": "NULL when unavailable, never zero. Never add across activities.",
            },
            "is_available": {"role": "attribute", **NEVER},
            "weekday_name": {"role": "dimension", **NEVER},
            "is_release_day": {"role": "dimension", **NEVER},
            "days_from_release": {"role": "dimension", **NEVER},
            "observed_at": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "What 'GitHub activity' counts",
                "chosen": "PRs opened, PRs merged, commits (GitHub Search API total_count)",
                "evidence": "request",
                "column": "activity",
                "detail": "user: metric 4 is GitHub PRs / commits; docs/metrics.md names the "
                "Search API `is:pr created:<day>`",
            },
            {
                "decision": "Day boundary",
                "chosen": "UTC day, first to last second",
                "evidence": "contract",
                "column": "activity_date",
                "detail": "config.py: all days in this study are UTC days",
            },
        ],
    },
    {
        "model": "fct_github_release_day_activities",
        "description": "Metric 4 breakdown: release day against the median of the same weekday "
        "in the weeks before it (canonical: the Thursday before), one row per activity.",
        "grain": ["activity"],
        "population": {
            "rule": "One row per activity present in fct_github_daily, whether or not release "
            "day has been counted yet.",
        },
        "columns": {
            "activity": {"role": "key", **NEVER},
            "activity_label": {"role": "attribute", **NEVER},
            "release_day": {"role": "time", **NEVER},
            "baseline_weeks": {"role": "attribute", **NEVER},
            "baseline_start": {"role": "attribute", **NEVER},
            "baseline_end": {"role": "attribute", **NEVER},
            "baseline_days_found": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "days",
                **NEVER,
            },
            "baseline_count": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "count",
                "null_rule": "NULL when no baseline day has a count.",
            },
            "release_day_count": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "count",
                "null_rule": "NULL until release day has ended and been counted.",
            },
            "pct_change": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "percent",
                "null_rule": "NULL unless release day and every baseline day have a count.",
            },
        },
        "assumptions": [
            {
                "decision": "What release day is compared with",
                "chosen": "the same weekday a week before (Thu 12 Nov 2026); a median when "
                "github_baseline_weeks > 1",
                "evidence": "data",
                "column": "baseline_count",
                "detail": "profiled (.dex/review/154): strong weekly cycle, and PRs opened grew "
                "from 1.15M (22 Oct) to 1.35M (12 Nov) on Thursdays, so older weeks understate a "
                "normal 19 Nov; commits carry bulk-import spikes (16.4M on 5 Nov vs ~12.9M), "
                "hence a median for longer baselines. No US holiday on 12 Nov",
            },
            {
                "decision": "A baseline day without a count",
                "chosen": "change NULL",
                "evidence": "default",
                "column": "pct_change",
                "detail": "an average over fewer days would be a different baseline",
            },
        ],
    },
    {
        "model": "fct_github_release_day",
        "description": "Metric 4 headline: the average of the activities' release-day changes, "
        "one row per release day, with its breakdown.",
        "grain": ["release_day_key"],
        "population": {"rule": "One row for the configured release day (var github_release_day)."},
        "columns": {
            "release_day_key": {"role": "key", **NEVER},
            "release_day": {"role": "time", **NEVER},
            "baseline_start": {"role": "attribute", **NEVER},
            "baseline_end": {"role": "attribute", **NEVER},
            "baseline_weeks": {"role": "attribute", **NEVER},
            "activities_total": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "count",
                **NEVER,
            },
            "activities_available": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "count",
                **NEVER,
            },
            "github_release_day_change": {
                "role": "measure",
                "aggregation": "max",
                "additivity": "non_additive",
                "unit": "percent",
                "null_rule": "NULL until every activity has a change.",
            },
            "breakdown": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "How the activities combine",
                "chosen": "plain average of the per-activity percent changes",
                "evidence": "precedent",
                "column": "github_release_day_change",
                "detail": "the Day-Off Index averages its phrases' changes the same way; counts "
                "differ by 10x between PRs and commits, so changes are averaged, not counts",
            },
            {
                "decision": "An activity not yet available",
                "chosen": "headline NULL",
                "evidence": "precedent",
                "column": "github_release_day_change",
                "detail": "fct_day_off_index: an average over fewer parts is a different number",
            },
        ],
    },
]

OUT.write_text(json.dumps({"edits": edits, "declarations": declarations}, indent=1) + "\n")
print(OUT)
