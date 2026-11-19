"""Build .dex/payloads/28-github-unit-tests.json: unit tests for Metric 4's release-day logic.
`transform test --scaffold` refuses these models (a jinja set block), so the tests are written
by hand. Run from the repo root: uv run python .dex/payloads/build_github_unit_tests.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def row(day: str, count, activity: str = "prs_opened") -> dict:
    labels = {"prs_opened": "PRs opened", "prs_merged": "PRs merged", "commits": "Commits"}
    return {"activity": activity, "activity_label": labels[activity], "activity_date": day,
            "activity_count": count}


DAILY = "ref('fct_github_daily')"
ACT = "ref('fct_github_release_day_activities')"
ACT_TESTS = [
    {
        "name": "github_release_day_vs_the_thursday_before",
        "description": "Release day against the same weekday a week before; other days and "
        "weekdays are ignored (a busy Wednesday must not move the baseline).",
        "model": "fct_github_release_day_activities",
        "overrides": {"vars": {"github_release_day": "2026-11-19", "github_baseline_weeks": 1}},
        "given": [{"input": DAILY, "rows": [
            row("2026-11-19", 750), row("2026-11-12", 1000), row("2026-11-18", 5000),
            row("2026-11-05", 9000), row("2026-11-20", 7000), row("2026-11-13", 3000),
        ]}],
        "expect": {"rows": [{"activity": "prs_opened", "baseline_start": "2026-11-12",
                             "baseline_end": "2026-11-12", "baseline_days_found": 1,
                             "baseline_count": 1000, "release_day_count": 750,
                             "pct_change": -25.0}]},
    },
    {
        "name": "github_release_day_not_counted_yet_is_null",
        "description": "Before release day has been counted the change is NULL, never -100%.",
        "model": "fct_github_release_day_activities",
        "overrides": {"vars": {"github_release_day": "2026-11-19", "github_baseline_weeks": 1}},
        "given": [{"input": DAILY, "rows": [row("2026-11-12", 1000), row("2026-11-19", None)]}],
        "expect": {"rows": [{"activity": "prs_opened", "baseline_count": 1000,
                             "release_day_count": None, "pct_change": None}]},
    },
    {
        "name": "github_longer_baseline_is_a_median_of_same_weekdays",
        "description": "Three weeks back: the median of the three Thursdays, so one bulk-import "
        "spike (9000) does not move it; the Thursday four weeks back is outside.",
        "model": "fct_github_release_day_activities",
        "overrides": {"vars": {"github_release_day": "2026-11-19", "github_baseline_weeks": 3}},
        "given": [{"input": DAILY, "rows": [
            row("2026-11-19", 1250, "commits"), row("2026-11-12", 1000, "commits"),
            row("2026-11-05", 9000, "commits"), row("2026-10-29", 800, "commits"),
            row("2026-10-22", 1, "commits"), row("2026-11-11", 50, "commits"),
        ]}],
        "expect": {"rows": [{"activity": "commits", "baseline_start": "2026-10-29",
                             "baseline_end": "2026-11-12", "baseline_days_found": 3,
                             "baseline_count": 1000, "release_day_count": 1250,
                             "pct_change": 25.0}]},
    },
    {
        "name": "github_zero_baseline_leaves_change_null",
        "description": "A baseline of zero has no percent change: NULL, never infinity.",
        "model": "fct_github_release_day_activities",
        "given": [{"input": DAILY, "rows": [row("2026-11-19", 5), row("2026-11-12", 0)]}],
        "expect": {"rows": [{"activity": "prs_opened", "baseline_count": 0,
                             "release_day_count": 5, "pct_change": None}]},
    },
    {
        "name": "github_missing_baseline_day_leaves_change_null",
        "description": "A baseline Thursday without a count makes the change NULL.",
        "model": "fct_github_release_day_activities",
        "overrides": {"vars": {"github_release_day": "2026-11-19", "github_baseline_weeks": 2}},
        "given": [{"input": DAILY, "rows": [
            row("2026-11-19", 1100), row("2026-11-12", 1000), row("2026-11-05", None),
        ]}],
        "expect": {"rows": [{"activity": "prs_opened", "baseline_days_found": 1,
                             "pct_change": None}]},
    },
]

HEAD_TESTS = [
    {
        "name": "github_headline_is_the_average_of_changes",
        "description": "The headline averages the activities' changes and spells each out.",
        "model": "fct_github_release_day",
        "given": [{"input": ACT, "rows": [
            {"activity": "prs_opened", "activity_label": "PRs opened", "release_day": "2026-11-19",
             "baseline_start": "2026-11-12", "baseline_end": "2026-11-12", "baseline_weeks": 1,
             "pct_change": -10.0},
            {"activity": "prs_merged", "activity_label": "PRs merged", "release_day": "2026-11-19",
             "baseline_start": "2026-11-12", "baseline_end": "2026-11-12", "baseline_weeks": 1,
             "pct_change": -5.0},
            {"activity": "commits", "activity_label": "Commits", "release_day": "2026-11-19",
             "baseline_start": "2026-11-12", "baseline_end": "2026-11-12", "baseline_weeks": 1,
             "pct_change": 3.0},
        ]}],
        "expect": {"rows": [{"release_day_key": "2026-11-19", "activities_total": 3,
                             "activities_available": 3, "github_release_day_change": -4.0,
                             "breakdown": "PRs opened -10.0% · PRs merged -5.0% · Commits +3.0%"}]},
    },
    {
        "name": "github_headline_null_until_every_activity_counted",
        "description": "One activity without a change leaves the headline NULL.",
        "model": "fct_github_release_day",
        "given": [{"input": ACT, "rows": [
            {"activity": "prs_opened", "activity_label": "PRs opened", "release_day": "2026-11-19",
             "baseline_start": "2026-11-12", "baseline_end": "2026-11-12", "baseline_weeks": 1,
             "pct_change": -10.0},
            {"activity": "commits", "activity_label": "Commits", "release_day": "2026-11-19",
             "baseline_start": "2026-11-12", "baseline_end": "2026-11-12", "baseline_weeks": 1,
             "pct_change": None},
        ]}],
        "expect": {"rows": [{"activities_available": 1, "github_release_day_change": None,
                             "breakdown": "PRs opened -10.0% · Commits not yet available"}]},
    },
]

edits = []
for path, tests in (("models/marts/fct_github_release_day_activities.yml", ACT_TESTS),
                    ("models/marts/fct_github_release_day.yml", HEAD_TESTS)):
    doc = yaml.safe_load((ROOT / path).read_text())
    doc["unit_tests"] = tests
    edits.append({"path": path, "kind": "schema_yml",
                  "content": yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)})
(ROOT / ".dex/payloads/28-github-unit-tests.json").write_text(
    json.dumps({"edits": edits}, indent=1, ensure_ascii=False) + "\n")
print("ok")
