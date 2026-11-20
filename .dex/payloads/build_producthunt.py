"""Build .dex/payloads/38-producthunt.json: Metric 5, did Product Hunt go quiet on GTA 6's release day?

The Product Hunt API v2 lands, per Pacific day, the day's launch count (raw.producthunt_days) and one
row per launch with its top-level comments written during its launch day (raw.producthunt_launches).
Release day is compared with the same weekday a week before, as Metric 4 does.
Run from the repo root: uv run python .dex/payloads/build_producthunt.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".dex/payloads/38-producthunt.json"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


# ---------------------------------------------------------------- project vars
project = yaml.safe_load(read("dbt_project.yml"))
project["vars"]["producthunt_release_day"] = "2026-11-19"
# 1 = the Thursday before (12 Nov 2026), Metric 4's baseline.
project["vars"]["producthunt_baseline_weeks"] = 1

# ---------------------------------------------------------------- sources
sources = yaml.safe_load(read("models/staging/_sources.yml"))
tables = sources["sources"][0]["tables"]
NEW_TABLES = [
    {
        "name": "producthunt_days",
        "description": (
            "Product Hunt API v2, one row per Pacific day: the API's totalCount of posts launched "
            "that day, how many the ingester listed, and the day's bounds in UTC."
        ),
    },
    {
        "name": "producthunt_launches",
        "description": (
            "Product Hunt API v2, one row per launch (post id): when it launched, whether Product "
            "Hunt featured it, its top-level comments written during its Pacific launch day, and "
            "its comment counts as of the pull. No names, taglines, comment text, usernames or URLs."
        ),
    },
]
for table in NEW_TABLES:
    if not any(t["name"] == table["name"] for t in tables):
        tables.append(table)

STG_DAYS = """-- One row per Pacific day Product Hunt was asked about (Metric 5). launches_total is the API's
-- own count of posts launched that day; is_complete says every one of them was listed and read.
select
    cast(day as date) as launch_day,
    day_start,
    day_end,
    cast(launches_total as bigint) as launches_total,
    cast(launches_listed as bigint) as launches_listed,
    coalesce(launches_listed = launches_total, false) as is_complete,
    observed_at
from {{ source('raw', 'producthunt_days') }}
"""

STG_LAUNCHES = """-- One row per Product Hunt launch (Metric 5): its Pacific launch day, and its top-level comments
-- written during that day. Counts and ids only.
select
    post_id,
    cast(day as date) as launch_day,
    launched_at,
    is_featured,
    cast(comments_launch_day as bigint) as comments_launch_day,
    cast(comments_top_level as bigint) as comments_top_level,
    cast(comments_total as bigint) as comments_total,
    observed_at
from {{ source('raw', 'producthunt_launches') }}
"""

INT_DAILY = """-- Metric 5: Product Hunt activity per Pacific day, one row per day per activity.
-- launches: the API's count of posts launched that day.
-- comments: top-level comments written on a launch during its launch day, over that day's launches.
-- A day not read in full has comments NULL (unavailable, never zero).
with days as (
    select * from {{ ref('stg_producthunt__days') }}
),

launches as (
    select
        launch_day,
        count(*) as launches_read,
        sum(comments_launch_day) as comments_launch_day
    from {{ ref('stg_producthunt__launches') }}
    group by launch_day
),

activities as (
    select * from (values ('launches', 1), ('comments', 2)) as a (activity, activity_order)
)

select
    days.launch_day,
    activities.activity,
    case activities.activity
        when 'launches' then days.launches_total
        when 'comments' then case
            when days.is_complete and coalesce(launches.launches_read, 0) = days.launches_total
                then coalesce(launches.comments_launch_day, 0)
        end
    end as activity_count,
    days.observed_at
from days
cross join activities
left join launches
    on days.launch_day = launches.launch_day
"""

DAILY = """-- Metric 5: Product Hunt activity per Pacific day. One row per day per activity, with the same
-- weekday a week earlier beside it (a date join, so a missing day cannot shift the pairing).
{%- set release_day = var('producthunt_release_day') %}
with daily as (
    select * from {{ ref('int_producthunt__daily') }}
)

select
    md5(daily.activity || '|' || cast(daily.launch_day as varchar)) as producthunt_day_key,
    daily.launch_day,
    daily.activity,
    case daily.activity
        when 'launches' then 'Launches'
        when 'comments' then 'Comments'
        else daily.activity
    end as activity_label,
    daily.activity_count,
    daily.activity_count is not null as is_available,
    daily.launch_day = date '{{ release_day }}' as is_release_day,
    cast(date_diff('day', date '{{ release_day }}', daily.launch_day) as integer)
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
    and week_before.launch_day = cast(daily.launch_day - 7 as date)
"""

ACTIVITIES = """-- Metric 5 breakdown: one row per Product Hunt activity. Release day's count against the median
-- of the same weekday in each of the weeks before it (vars producthunt_release_day and
-- producthunt_baseline_weeks; canonical: Thu 19 Nov 2026 vs the Thursday before, 12 Nov).
{%- set release_day = var('producthunt_release_day') %}
{%- set weeks = var('producthunt_baseline_weeks', 1) %}
with params as (
    select
        date '{{ release_day }}' as release_day,
        cast({{ weeks }} as integer) as baseline_weeks,
        cast(date '{{ release_day }}' - 7 * {{ weeks }} as date) as baseline_start,
        cast(date '{{ release_day }}' - 7 as date) as baseline_end
),

activities as (
    select distinct activity, activity_label
    from {{ ref('fct_producthunt_daily') }}
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
            where daily.launch_day = params.release_day
        ) as release_day_count,
        median(daily.activity_count) filter (
            where daily.launch_day between params.baseline_start and params.baseline_end
                and dayofweek(daily.launch_day) = dayofweek(params.release_day)
        ) as baseline_count,
        count(daily.activity_count) filter (
            where daily.launch_day between params.baseline_start and params.baseline_end
                and dayofweek(daily.launch_day) = dayofweek(params.release_day)
        ) as baseline_days_found
    from activities
    cross join params
    left join {{ ref('fct_producthunt_daily') }} as daily
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

HEADLINE = """-- Metric 5 headline: launches and comments on release day against the Thursday before, in
-- percent, one row per release day, with `breakdown` spelling out both.
select
    cast(release_day as varchar) as release_day_key,
    min(release_day) as release_day,
    min(baseline_start) as baseline_start,
    min(baseline_end) as baseline_end,
    min(baseline_weeks) as baseline_weeks,
    count(*) as activities_total,
    count(pct_change) as activities_available,
    max(pct_change) filter (where activity = 'launches') as producthunt_launches_change,
    max(pct_change) filter (where activity = 'comments') as producthunt_comments_change,
    string_agg(
        activity_label || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by activity desc
    ) as breakdown
from {{ ref('fct_producthunt_release_day_activities') }}
group by release_day
"""

TEST = """-- The Product Hunt release-day changes never travel without their breakdown.
select *
from {{ ref('fct_producthunt_release_day') }}
where (producthunt_launches_change is not null or producthunt_comments_change is not null)
    and breakdown is null
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


DESC = {
    "stg_producthunt__days": "Product Hunt launch counts, one row per Pacific day.",
    "stg_producthunt__launches": "Product Hunt launches, one row per launch (post id).",
    "int_producthunt__daily": "Metric 5: Product Hunt launches and launch-day comments per Pacific "
    "day, one row per day per activity.",
    "fct_producthunt_daily": "Metric 5: Product Hunt activity per Pacific day, one row per day per "
    "activity, with the same weekday a week earlier.",
    "fct_producthunt_release_day_activities": "Metric 5 breakdown: release day against the same "
    "weekday in the weeks before (canonical: the Thursday before), one row per activity.",
    "fct_producthunt_release_day": "Metric 5 headline: launches and comments on release day "
    "against the Thursday before, one row per release day, with its breakdown.",
}
COLS = {
    "stg_producthunt__days": {
        "launch_day": "Pacific day (Product Hunt's day).",
        "day_start": "The day's first instant, UTC.",
        "day_end": "The next day's first instant, UTC.",
        "launches_total": "The API's count of posts launched that day.",
        "launches_listed": "Launches the ingester listed and read.",
        "is_complete": "True when every launch was listed.",
        "observed_at": "When we asked (UTC).",
    },
    "stg_producthunt__launches": {
        "post_id": "Product Hunt's numeric post id.",
        "launch_day": "Pacific day it launched.",
        "launched_at": "When it launched (UTC).",
        "is_featured": "True when Product Hunt featured it on the homepage.",
        "comments_launch_day": "Top-level comments written during its Pacific launch day.",
        "comments_top_level": "Top-level comments as of the pull.",
        "comments_total": "All comments including replies, as of the pull.",
        "observed_at": "When we asked (UTC).",
    },
    "int_producthunt__daily": {
        "launch_day": "Pacific day.",
        "activity": "launches or comments.",
        "activity_count": "How many on the day. NULL when unavailable, never zero.",
        "observed_at": "When the day was asked for (UTC).",
    },
    "fct_producthunt_daily": {
        "producthunt_day_key": "md5 of activity|day.",
        "launch_day": "Pacific day.",
        "activity": "launches or comments.",
        "activity_label": "Launches or Comments.",
        "activity_count": "How many on the day. NULL when unavailable, never zero.",
        "is_available": "True when the day has a count.",
        "is_release_day": "True on GTA 6's release day (var producthunt_release_day).",
        "days_from_release": "Days after release day (negative before it).",
        "observed_at": "When the day was asked for (UTC).",
        "prior_week_count": "The same weekday 7 days earlier.",
        "wow_pct_change": "The day against the same weekday 7 days earlier, in percent.",
    },
    "fct_producthunt_release_day_activities": {
        "activity": "launches or comments.",
        "activity_label": "Launches or Comments.",
        "release_day": "GTA 6's release day (var producthunt_release_day).",
        "baseline_weeks": "How many same weekdays before release day form the baseline.",
        "baseline_start": "First baseline day.",
        "baseline_end": "Last baseline day (a week before release day).",
        "baseline_days_found": "Baseline days with a count.",
        "baseline_count": "Median count over the baseline days (the day itself when there is one).",
        "release_day_count": "Count on release day. NULL until the day is over and counted.",
        "pct_change": "Release day against the baseline, in percent.",
    },
    "fct_producthunt_release_day": {
        "release_day_key": "Release day as text: the row's key.",
        "release_day": "GTA 6's release day.",
        "baseline_start": "First baseline day.",
        "baseline_end": "Last baseline day.",
        "baseline_weeks": "Baseline days (same weekday, weeks before).",
        "activities_total": "Activities in the breakdown.",
        "activities_available": "Activities with a change.",
        "producthunt_launches_change": "Launches on release day against the baseline, in percent.",
        "producthunt_comments_change": "Launch-day comments on release day against the baseline, "
        "in percent.",
        "breakdown": "Both activities' changes. Always report it with the headline.",
    },
}
SQL = {
    "stg_producthunt__days": ("models/staging", STG_DAYS),
    "stg_producthunt__launches": ("models/staging", STG_LAUNCHES),
    "int_producthunt__daily": ("models/intermediate", INT_DAILY),
    "fct_producthunt_daily": ("models/marts", DAILY),
    "fct_producthunt_release_day_activities": ("models/marts", ACTIVITIES),
    "fct_producthunt_release_day": ("models/marts", HEADLINE),
}

edits = [
    {"path": "dbt_project.yml", "kind": "project_yml", "content": dump(project)},
    {"path": "models/staging/_sources.yml", "kind": "schema_yml", "content": dump(sources)},
]
for name, (folder, sql) in SQL.items():
    edits.append({"path": f"{folder}/{name}.sql", "kind": "model_sql", "content": sql})
    edits.append(
        {
            "path": f"{folder}/{name}.yml",
            "kind": "schema_yml",
            "content": model_yml(name, DESC[name], COLS[name]),
        }
    )
edits.append(
    {
        "path": "data_tests/assert_producthunt_release_day_has_breakdown.sql",
        "kind": "test_sql",
        "content": TEST,
    }
)

NEVER = {"null_rule": "never"}
COUNT = {"role": "measure", "aggregation": "sum", "additivity": "additive", "unit": "count"}
SNAP = {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "count"}
PCT = {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "percent"}

declarations = [
    {
        "model": "stg_producthunt__days",
        "description": DESC["stg_producthunt__days"],
        "grain": ["launch_day"],
        "population": {"rule": "Every ended Pacific day the ingester asked for; newest pull wins."},
        "columns": {
            "launch_day": {"role": "time", **NEVER},
            "day_start": {"role": "attribute", **NEVER},
            "day_end": {"role": "attribute", **NEVER},
            "launches_total": {**COUNT, **NEVER},
            "launches_listed": {**COUNT, **NEVER},
            "is_complete": {"role": "attribute", **NEVER},
            "observed_at": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "Day boundary",
                "chosen": "Pacific day (America/Los_Angeles), Product Hunt's own day",
                "evidence": "data",
                "column": "launch_day",
                "detail": "Product Hunt launches at 00:01 Pacific (API createdAt 08:01Z in "
                "November); a UTC day would split each launch day in two. Metric 4 uses UTC days",
            }
        ],
    },
    {
        "model": "stg_producthunt__launches",
        "description": DESC["stg_producthunt__launches"],
        "grain": ["post_id"],
        "population": {"rule": "Every launch listed for an asked day; newest pull wins."},
        "columns": {
            "post_id": {"role": "key", **NEVER},
            "launch_day": {"role": "time", **NEVER},
            "launched_at": {"role": "attribute", **NEVER},
            "is_featured": {"role": "dimension", **NEVER},
            "comments_launch_day": {**COUNT, **NEVER},
            "comments_top_level": {**SNAP, **NEVER},
            "comments_total": {**SNAP, **NEVER},
            "observed_at": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "Which comments count",
                "chosen": "top-level comments written during the launch's Pacific launch day",
                "evidence": "data",
                "column": "comments_launch_day",
                "detail": "a launch a week old has had a week more to collect comments, so only "
                "launch-day comments compare two days fairly; the API refuses reply timestamps "
                "at a day's volume (complexity cap 500,000), so replies are left out",
            }
        ],
    },
    {
        "model": "int_producthunt__daily",
        "description": DESC["int_producthunt__daily"],
        "grain": ["launch_day", "activity"],
        "population": {
            "rule": "Every asked day in stg_producthunt__days, once per activity (launches, "
            "comments).",
        },
        "columns": {
            "launch_day": {"role": "time", **NEVER},
            "activity": {"role": "dimension", **NEVER},
            "activity_count": {
                **COUNT,
                "null_rule": "comments NULL when the day was not read in full; never zero for "
                "unavailable.",
            },
            "observed_at": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "Which days exist",
                "chosen": "every day in stg_producthunt__days, crossed with both activities",
                "evidence": "precedent",
                "column": "launch_day",
                "detail": "driven from the day roster so a day with no launches read keeps a row; "
                "fct_github_daily keeps every asked (day, activity) the same way",
            },
            {
                "decision": "What 'Product Hunt activity' counts",
                "chosen": "launches (count of posts launched) and comments; not points",
                "evidence": "request",
                "column": "activity",
                "detail": "user: points is not a good metric; count of launches and total "
                "count of comments is",
            },
            {
                "decision": "Which launches count",
                "chosen": "every post launched that day, featured or not",
                "evidence": "default",
                "column": "activity_count",
                "detail": "the API's totalCount for the day; featured launches are ~3% of them "
                "(33 of 1,197 on 19 Nov) and stay in staging as is_featured",
            },
            {
                "decision": "A day not read in full",
                "chosen": "comments NULL; launches still the API's count",
                "evidence": "contract",
                "column": "activity_count",
                "detail": "AGENTS.md: a NULL is unavailable, never zero",
            },
        ],
    },
    {
        "model": "fct_producthunt_daily",
        "description": DESC["fct_producthunt_daily"],
        "grain": ["launch_day", "activity"],
        "population": {
            "rule": "Every (day, activity) row in int_producthunt__daily.",
            "parent": {
                "model": "int_producthunt__daily",
                "key": {"launch_day": "launch_day", "activity": "activity"},
            },
        },
        "columns": {
            "producthunt_day_key": {"role": "key", **NEVER},
            "launch_day": {"role": "time", **NEVER},
            "activity": {"role": "dimension", **NEVER},
            "activity_label": {"role": "attribute", **NEVER},
            "activity_count": {
                **COUNT,
                "null_rule": "NULL when unavailable, never zero. Never add across activities.",
            },
            "is_available": {"role": "attribute", **NEVER},
            "is_release_day": {"role": "dimension", **NEVER},
            "days_from_release": {"role": "dimension", **NEVER},
            "observed_at": {"role": "attribute", **NEVER},
            "prior_week_count": {**SNAP, "null_rule": "NULL when that day has no count."},
            "wow_pct_change": {**PCT, "null_rule": "NULL unless both days have a count."},
        },
        "assumptions": [
            {
                "decision": "Week-before pairing",
                "chosen": "date join to the same activity 7 days earlier",
                "evidence": "precedent",
                "column": "prior_week_count",
                "detail": "fct_github_daily pairs days the same way, so a missing day cannot "
                "shift the pairing",
            }
        ],
    },
    {
        "model": "fct_producthunt_release_day_activities",
        "description": DESC["fct_producthunt_release_day_activities"],
        "grain": ["activity"],
        "population": {
            "rule": "One row per activity present in fct_producthunt_daily, whether or not "
            "release day has been counted yet.",
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
            "baseline_count": {**SNAP, "null_rule": "NULL when no baseline day has a count."},
            "release_day_count": {
                **SNAP,
                "null_rule": "NULL until release day has ended and been counted.",
            },
            "pct_change": {
                **PCT,
                "null_rule": "NULL unless release day and every baseline day have a count.",
            },
        },
        "assumptions": [
            {
                "decision": "Which rows exist",
                "chosen": "one row per activity in fct_producthunt_daily (launches, comments); "
                "not a child of the GitHub marts Dex drafted as parent",
                "evidence": "precedent",
                "column": "activity",
                "detail": "mirrors fct_github_release_day_activities, driven from its own daily mart",
            },
            {
                "decision": "What release day is compared with",
                "chosen": "the same weekday a week before (Thu 12 Nov 2026)",
                "evidence": "precedent",
                "column": "baseline_count",
                "detail": "Metric 4 (fct_github_release_day_activities) compares with the "
                "Thursday before; launch counts have a strong weekly cycle (818 on Sun 15 Nov "
                "vs 1,175 on Thu 12 Nov)",
            },
            {
                "decision": "A baseline day without a count",
                "chosen": "change NULL",
                "evidence": "precedent",
                "column": "pct_change",
                "detail": "fct_github_release_day_activities does the same",
            },
        ],
    },
    {
        "model": "fct_producthunt_release_day",
        "description": DESC["fct_producthunt_release_day"],
        "grain": ["release_day_key"],
        "population": {
            "rule": "One row for the configured release day (var producthunt_release_day)."
        },
        "columns": {
            "release_day_key": {"role": "key", **NEVER},
            "release_day": {"role": "time", **NEVER},
            "baseline_start": {"role": "attribute", **NEVER},
            "baseline_end": {"role": "attribute", **NEVER},
            "baseline_weeks": {"role": "attribute", **NEVER},
            "activities_total": {**SNAP, **NEVER},
            "activities_available": {**SNAP, **NEVER},
            "producthunt_launches_change": {
                **PCT,
                "null_rule": "NULL until launches have a change.",
            },
            "producthunt_comments_change": {
                **PCT,
                "null_rule": "NULL until comments have a change.",
            },
            "breakdown": {"role": "attribute", **NEVER},
        },
        "assumptions": [
            {
                "decision": "Which rows exist",
                "chosen": "one row for the configured release day; not a child of "
                "fct_github_release_day, which Dex drafted as parent",
                "evidence": "precedent",
                "column": "release_day_key",
                "detail": "mirrors fct_github_release_day, one row per release day",
            },
            {
                "decision": "The headline",
                "chosen": "two numbers side by side, launches and comments; no average",
                "evidence": "request",
                "column": "producthunt_launches_change",
                "detail": "user: count of launches and total count of comments are the metrics; "
                "Metric 4's headline is one activity, not an average (user, 2026-11-20)",
            }
        ],
    },
]

OUT.write_text(json.dumps({"edits": edits, "declarations": declarations}, indent=1) + "\n")
print(OUT)
