"""Build .dex/payloads/35-github-significance.json: is release day's drop bigger than GitHub's
ordinary day-to-day noise? A pre-declared test, with placebos.

Primary test, per activity: fit log(daily count) = a level per weekday + one linear trend on
every counted day before the candidate day, predict the candidate, and take the gap in
prediction standard errors (t, df = fit days - weekdays - 1). Release day is one candidate;
every earlier candidate with enough history is a placebo (the same test where nothing happened).
Thursday check: release day's week-on-week change against the earlier Thursdays' changes.
Run from the repo root: uv run python .dex/payloads/build_github_test.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

project = yaml.safe_load((ROOT / "dbt_project.yml").read_text())
# A candidate day is scored only with at least three weeks of history behind it.
project["vars"]["github_test_min_fit_days"] = 21

SURPRISE = """-- Metric 4 backup: how far each day's count lands from what the days before it predict.
-- Per activity and candidate day: fit log(count) = a level per weekday + one linear trend on
-- the counted days BEFORE the candidate only, predict the candidate, and measure the gap in
-- prediction standard errors. Release day is one candidate; the earlier ones are placebos.
{%- set release_day = var('github_release_day') %}
{%- set min_fit_days = var('github_test_min_fit_days', 21) %}
with daily as (
    select
        activity,
        activity_date,
        ln(activity_count) as y,
        cast(date_diff('day', date '{{ release_day }}', activity_date) as double) as t,
        isodow(activity_date) as dow
    from {{ ref('fct_github_daily') }}
    where activity_count > 0
        and activity_date <= date '{{ release_day }}'
),

fit as (
    select
        candidate.activity,
        candidate.activity_date as candidate_date,
        history.y,
        history.t,
        history.dow
    from daily as candidate
    inner join daily as history
        on candidate.activity = history.activity
        and history.activity_date < candidate.activity_date
),

weekday_means as (
    select
        activity,
        candidate_date,
        dow,
        avg(t) as mean_t,
        avg(y) as mean_y,
        count(*) as weekday_days
    from fit
    group by activity, candidate_date, dow
),

centered as (
    select
        fit.activity,
        fit.candidate_date,
        fit.t - weekday_means.mean_t as tc,
        fit.y - weekday_means.mean_y as yc
    from fit
    inner join weekday_means
        on fit.activity = weekday_means.activity
        and fit.candidate_date = weekday_means.candidate_date
        and fit.dow = weekday_means.dow
),

trend as (
    select
        activity,
        candidate_date,
        count(*) as fit_days,
        sum(tc * yc) / nullif(sum(tc * tc), 0) as daily_trend,
        sum(tc * tc) as sxx
    from centered
    group by activity, candidate_date
),

weekdays as (
    select activity, candidate_date, count(*) as weekdays
    from weekday_means
    group by activity, candidate_date
),

residuals as (
    select
        centered.activity,
        centered.candidate_date,
        sum(power(centered.yc - trend.daily_trend * centered.tc, 2)) as ssr
    from centered
    inner join trend
        on centered.activity = trend.activity
        and centered.candidate_date = trend.candidate_date
    group by centered.activity, centered.candidate_date
),

scored as (
    select
        daily.activity,
        daily.activity_date as candidate_date,
        trend.fit_days,
        trend.fit_days - weekdays.weekdays - 1 as df,
        trend.daily_trend,
        weekday_means.mean_y + trend.daily_trend * (daily.t - weekday_means.mean_t)
            as expected_log,
        daily.y as observed_log,
        residuals.ssr / nullif(trend.fit_days - weekdays.weekdays - 1, 0) as residual_var,
        1 + 1.0 / weekday_means.weekday_days
            + power(daily.t - weekday_means.mean_t, 2) / nullif(trend.sxx, 0) as variance_factor
    from daily
    inner join trend
        on daily.activity = trend.activity
        and daily.activity_date = trend.candidate_date
    inner join weekdays
        on daily.activity = weekdays.activity
        and daily.activity_date = weekdays.candidate_date
    inner join residuals
        on daily.activity = residuals.activity
        and daily.activity_date = residuals.candidate_date
    inner join weekday_means
        on daily.activity = weekday_means.activity
        and daily.activity_date = weekday_means.candidate_date
        and daily.dow = weekday_means.dow
)

select
    md5(activity || '|' || cast(candidate_date as varchar)) as github_surprise_key,
    activity,
    candidate_date,
    candidate_date = date '{{ release_day }}' as is_release_day,
    fit_days,
    df,
    daily_trend,
    exp(expected_log) as expected_count,
    exp(observed_log) as observed_count,
    100 * (exp(observed_log - expected_log) - 1) as pct_vs_expected,
    case
        when fit_days >= {{ min_fit_days }} and df >= 5 and residual_var > 0
            then (observed_log - expected_log) / sqrt(residual_var * variance_factor)
    end as t_stat
from scored
"""

TEST = """-- Metric 4 backup: the release-day test, one row per activity. The primary test (release
-- day against the weekday-and-trend prediction from the days before it), its placebo rank
-- among the earlier days, and the Thursday check (release day's week-on-week change against
-- the earlier same-weekday changes). p-values are read from t and df downstream.
{%- set release_day = var('github_release_day') %}
with surprise as (
    select * from {{ ref('fct_github_day_surprise') }}
),

release as (
    select * from surprise where is_release_day
),

placebos as (
    select
        release.activity,
        count(surprise.t_stat) as placebo_days,
        count(surprise.t_stat) filter (where surprise.t_stat <= release.t_stat)
            as placebo_days_as_low
    from release
    left join surprise
        on release.activity = surprise.activity
        and surprise.candidate_date < release.candidate_date
    group by release.activity
),

weekday as (
    select
        activity,
        count(wow_pct_change) filter (where not is_release_day) as weekday_n,
        avg(wow_pct_change) filter (where not is_release_day) as weekday_wow_mean,
        stddev_samp(wow_pct_change) filter (where not is_release_day) as weekday_wow_sd,
        max(wow_pct_change) filter (where is_release_day) as release_wow
    from {{ ref('fct_github_daily') }}
    where dayofweek(activity_date) = dayofweek(date '{{ release_day }}')
        and activity_date <= date '{{ release_day }}'
    group by activity
)

select
    release.activity,
    release.candidate_date as release_day,
    release.fit_days,
    release.df,
    release.expected_count,
    release.observed_count,
    release.pct_vs_expected,
    release.t_stat,
    placebos.placebo_days,
    placebos.placebo_days_as_low,
    case
        when release.t_stat is not null and placebos.placebo_days > 0
            then (placebos.placebo_days_as_low + 1.0) / (placebos.placebo_days + 1)
    end as placebo_p,
    weekday.weekday_n,
    weekday.weekday_wow_mean,
    weekday.weekday_wow_sd,
    weekday.release_wow,
    case
        when weekday.weekday_n >= 3 and weekday.weekday_wow_sd > 0
            then (weekday.release_wow - weekday.weekday_wow_mean)
                / (weekday.weekday_wow_sd * sqrt(1 + 1.0 / weekday.weekday_n))
    end as weekday_t,
    weekday.weekday_n - 1 as weekday_df
from release
inner join placebos
    on release.activity = placebos.activity
left join weekday
    on release.activity = weekday.activity
"""


def model_yml(name, description, columns, unit_tests=None):
    doc = {"version": 2, "models": [{"name": name, "description": description,
                                     "columns": [{"name": c, "description": d}
                                                 for c, d in columns.items()]}]}
    if unit_tests:
        doc["unit_tests"] = unit_tests
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


SURPRISE_COLS = {
    "github_surprise_key": "md5 of activity|candidate day.",
    "activity": "prs_opened, prs_merged or commits.",
    "candidate_date": "The day scored.",
    "is_release_day": "True on GTA 6's release day; every other row is a placebo.",
    "fit_days": "Counted days before the candidate the model was fitted on.",
    "df": "Degrees of freedom: fit days - weekdays - 1.",
    "daily_trend": "Fitted trend, log points per day.",
    "expected_count": "What the days before predict for the candidate.",
    "observed_count": "The candidate's count.",
    "pct_vs_expected": "Observed against expected, in percent.",
    "t_stat": "Gap in prediction standard errors. NULL with under the minimum history.",
}
TEST_COLS = {
    "activity": "prs_opened, prs_merged or commits.",
    "release_day": "GTA 6's release day.",
    "fit_days": "Days the release-day prediction was fitted on.",
    "df": "Degrees of freedom of the primary test.",
    "expected_count": "Release day as predicted from the days before it.",
    "observed_count": "Release day as counted.",
    "pct_vs_expected": "Observed against expected, in percent.",
    "t_stat": "Primary test statistic (Student t, df above).",
    "placebo_days": "Earlier days scored the same way.",
    "placebo_days_as_low": "Placebo days with a t at or below release day's.",
    "placebo_p": "(as low + 1) / (placebo days + 1): the share of days, release day included, "
    "this far below their prediction.",
    "weekday_n": "Earlier same-weekday week-on-week changes.",
    "weekday_wow_mean": "Their mean, in percent.",
    "weekday_wow_sd": "Their standard deviation, in percent points.",
    "release_wow": "Release day's week-on-week change, in percent.",
    "weekday_t": "Release day's change against the earlier ones, in prediction SDs.",
    "weekday_df": "weekday_n - 1.",
}


def drow(day, count, activity="prs_opened", wow=None):
    return {"activity": activity, "activity_date": day, "activity_count": count,
            "is_release_day": day == "2026-11-19", "wow_pct_change": wow}


# Unit tests pin the structure (only earlier days enter a fit; the minimum history; NULLs),
# not floating-point regression output, which `gta6 charts` cross-checks against numpy.
DAILY = "ref('fct_github_daily')"
weeks = ["2026-10-22", "2026-10-29", "2026-11-05", "2026-11-12"]
wednesdays = ["2026-10-21", "2026-10-28", "2026-11-04", "2026-11-11", "2026-11-18"]
SURPRISE_TESTS = [
    {
        "name": "github_surprise_fits_only_on_earlier_days",
        "description": "Each candidate is fitted on the days before it only: a later day never "
        "enters, and history under the minimum leaves t NULL.",
        "model": "fct_github_day_surprise",
        "overrides": {"vars": {"github_release_day": "2026-11-19",
                               "github_test_min_fit_days": 7}},
        "given": [{"input": DAILY, "rows": (
            [drow(d, 1000 + 10 * i) for i, d in enumerate(weeks)]
            + [drow(d, 900 + 7 * i + (5 if i % 2 else 0)) for i, d in enumerate(wednesdays)]
            + [drow("2026-11-19", 800), drow("2026-11-20", 99999)]
        )}],
        "expect": {"rows": [
            {"candidate_date": "2026-11-19", "is_release_day": True, "fit_days": 9, "df": 6},
            {"candidate_date": "2026-11-18", "is_release_day": False, "fit_days": 8, "df": 5},
            {"candidate_date": "2026-11-12", "is_release_day": False, "fit_days": 7, "df": 4},
            {"candidate_date": "2026-11-11", "is_release_day": False, "fit_days": 6, "df": 3},
            {"candidate_date": "2026-11-05", "is_release_day": False, "fit_days": 5, "df": 2},
            {"candidate_date": "2026-11-04", "is_release_day": False, "fit_days": 4, "df": 1},
            {"candidate_date": "2026-10-29", "is_release_day": False, "fit_days": 3, "df": 0},
            {"candidate_date": "2026-10-28", "is_release_day": False, "fit_days": 2, "df": -1},
        ]},
    },
]


def trow(day, t, release=False, activity="prs_opened"):
    return {"activity": activity, "candidate_date": day, "is_release_day": release,
            "fit_days": 30, "df": 22, "expected_count": 100.0, "observed_count": 100.0,
            "pct_vs_expected": 0.0, "t_stat": t}


TEST_TESTS = [
    {
        "name": "github_placebo_p_counts_days_as_low_as_release",
        "description": "placebo_p = (placebos at or below release day's t + 1) / (placebos + 1); "
        "later days and NULL placebos do not count.",
        "model": "fct_github_release_day_test",
        "overrides": {"vars": {"github_release_day": "2026-11-19"}},
        "given": [
            {"input": "ref('fct_github_day_surprise')", "rows": [
                trow("2026-11-19", -2.0, True), trow("2026-11-18", -2.5),
                trow("2026-11-17", -2.0), trow("2026-11-16", 1.0), trow("2026-11-15", 0.5),
                trow("2026-11-14", None), trow("2026-11-20", -9.0)]},
            {"input": DAILY, "rows": [
                drow("2026-10-29", 1, wow=2.0), drow("2026-11-05", 1, wow=4.0),
                drow("2026-11-12", 1, wow=6.0), drow("2026-11-19", 1, wow=-4.0)]},
        ],
        "expect": {"rows": [{"activity": "prs_opened", "placebo_days": 4,
                             "placebo_days_as_low": 2, "placebo_p": 0.6,
                             "weekday_n": 3, "weekday_wow_mean": 4.0, "weekday_wow_sd": 2.0,
                             "release_wow": -4.0, "weekday_df": 2}]},
    },
    {
        "name": "github_test_null_without_release_t",
        "description": "No release-day t (too little history): placebo_p is NULL.",
        "model": "fct_github_release_day_test",
        "overrides": {"vars": {"github_release_day": "2026-11-19"}},
        "given": [
            {"input": "ref('fct_github_day_surprise')", "rows": [
                trow("2026-11-19", None, True), trow("2026-11-18", -1.0)]},
            {"input": DAILY, "rows": [drow("2026-11-19", 1, wow=None)]},
        ],
        "expect": {"rows": [{"activity": "prs_opened", "placebo_days": 1,
                             "placebo_days_as_low": 0, "placebo_p": None, "weekday_t": None}]},
    },
]

NEVER = {"null_rule": "never"}


def measure(unit, null_rule="never", additivity="non_additive"):
    return {"role": "measure", "aggregation": "max", "additivity": additivity, "unit": unit,
            "null_rule": null_rule}


declarations = [
    {
        "model": "fct_github_day_surprise",
        "description": "Metric 4 backup: each counted day against the weekday-and-trend "
        "prediction from the days before it. One row per activity per day up to release day "
        "with a same-weekday day before it; release day is one row, the rest are placebos.",
        "grain": ["activity", "candidate_date"],
        "population": {
            "rule": "Every counted day up to release day with at least one earlier day on the "
            "same weekday (the first week cannot be predicted); days after release day and "
            "days without a count are not candidates.",
        },
        "columns": {
            "github_surprise_key": {"role": "attribute", **NEVER},
            "activity": {"role": "dimension", **NEVER},
            "candidate_date": {"role": "time", **NEVER},
            "is_release_day": {"role": "dimension", **NEVER},
            "fit_days": measure("days"),
            "df": measure("count"),
            "daily_trend": measure("log points per day",
                                   "NULL while every weekday has a single day (no trend yet)."),
            "expected_count": measure("count", "NULL while there is no trend yet."),
            "observed_count": measure("count"),
            "pct_vs_expected": measure("percent", "NULL while there is no trend yet."),
            "t_stat": measure("standard errors", "NULL under the minimum history or df < 5."),
        },
        "assumptions": [
            {"decision": "What 'normal' release day would have been",
             "chosen": "log(count) = weekday level + linear trend, fitted on every counted day "
             "before the candidate; one-sided t on the prediction error",
             "evidence": "request", "column": "t_stat",
             "detail": "user, 20 Nov: a formal hypothesis test that the drop is significant; "
             "the model was fixed before the result was computed: weekday levels for the weekly "
             "cycle, a trend for GitHub's growth, logs so changes are relative"},
            {"decision": "Placebos",
             "chosen": "the same test on every earlier day with >= 21 days of history",
             "evidence": "default", "column": "is_release_day",
             "detail": "an empirical check that does not lean on the t distribution: how often "
             "an ordinary day lands this far below its prediction"},
            {"decision": "Which days are candidates",
             "chosen": "counted days up to release day with an earlier same-weekday day; the "
             "first week, later days and uncounted days are left out",
             "evidence": "request", "column": "candidate_date",
             "detail": "user, 20 Nov: test 19 Nov against what came before it; a day with "
             "nothing before it cannot be predicted, and a day after release is not a placebo"},
        ],
    },
    {
        "model": "fct_github_release_day_test",
        "description": "Metric 4 backup: the release-day hypothesis test, one row per activity.",
        "grain": ["activity"],
        "population": {"rule": "One row per activity with a release-day row in "
                       "fct_github_day_surprise.",
                       "parent": {"model": "fct_github_release_day_activities",
                                  "key": {"activity": "activity"}}},
        "columns": {
            "activity": {"role": "key", **NEVER},
            "release_day": {"role": "time", **NEVER},
            "fit_days": measure("days"),
            "df": measure("count"),
            "expected_count": measure("count"),
            "observed_count": measure("count"),
            "pct_vs_expected": measure("percent"),
            "t_stat": measure("standard errors", "NULL under the minimum history."),
            "placebo_days": measure("count"),
            "placebo_days_as_low": measure("count"),
            "placebo_p": measure("fraction", "NULL without a release-day t."),
            "weekday_n": measure("count"),
            "weekday_wow_mean": measure("percent", "NULL without earlier changes."),
            "weekday_wow_sd": measure("percent", "NULL with fewer than two."),
            "release_wow": measure("percent", "NULL when either day is missing."),
            "weekday_t": measure("standard errors", "NULL with fewer than 3 earlier changes."),
            "weekday_df": measure("count", "NULL without earlier changes."),
        },
        "assumptions": [
            {"decision": "Placebo p-value",
             "chosen": "(placebo days at or below release day's t + 1) / (placebo days + 1)",
             "evidence": "default", "column": "placebo_p",
             "detail": "the standard rank p-value that counts release day itself, so it is "
             "never zero"},
            {"decision": "Thursday check",
             "chosen": "release day's week-on-week change against the earlier same-weekday "
             "changes, prediction t with n - 1 df",
             "evidence": "default", "column": "weekday_t",
             "detail": "uses only the Thursdays, with no model of the trend"},
        ],
    },
]

edits = [
    {"path": "dbt_project.yml", "kind": "project_yml",
     "content": yaml.safe_dump(project, sort_keys=False, width=100, allow_unicode=True)},
    {"path": "models/marts/fct_github_day_surprise.sql", "kind": "model_sql",
     "content": SURPRISE},
    {"path": "models/marts/fct_github_day_surprise.yml", "kind": "schema_yml",
     "content": model_yml("fct_github_day_surprise", declarations[0]["description"],
                          SURPRISE_COLS, SURPRISE_TESTS)},
    {"path": "models/marts/fct_github_release_day_test.sql", "kind": "model_sql",
     "content": TEST},
    {"path": "models/marts/fct_github_release_day_test.yml", "kind": "schema_yml",
     "content": model_yml("fct_github_release_day_test", declarations[1]["description"],
                          TEST_COLS, TEST_TESTS)},
]
(ROOT / ".dex/payloads/35-github-significance.json").write_text(
    json.dumps({"edits": edits, "declarations": declarations}, indent=1, ensure_ascii=False)
    + "\n")
print("ok")
