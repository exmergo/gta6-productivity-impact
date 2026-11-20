"""Build .dex/payloads/29-github-headline.json: Metric 4's headline becomes PRs opened's
release-day change (was the average of the three activities). The breakdown stays.
Run from the repo root: uv run python .dex/payloads/build_github_headline.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
YML = "models/marts/fct_github_release_day.yml"

SQL = """-- Metric 4 headline: PRs opened on release day against the Thursday before, in percent, one
-- row per release day. It carries its breakdown: `breakdown` spells out every activity's
-- change (PRs opened, PRs merged, commits), so the headline is never read without it.
select
    cast(release_day as varchar) as release_day_key,
    min(release_day) as release_day,
    min(baseline_start) as baseline_start,
    min(baseline_end) as baseline_end,
    min(baseline_weeks) as baseline_weeks,
    count(*) as activities_total,
    count(pct_change) as activities_available,
    max(pct_change) filter (where activity = 'prs_opened') as github_release_day_change,
    string_agg(
        activity_label || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by activity desc
    ) as breakdown
from {{ ref('fct_github_release_day_activities') }}
group by release_day
"""

TEST = """-- The GitHub release-day headline never travels without its breakdown.
select *
from {{ ref('fct_github_release_day') }}
where github_release_day_change is not null
    and breakdown is null
"""


def act(activity: str, label: str, change) -> dict:
    return {"activity": activity, "activity_label": label, "release_day": "2026-11-19",
            "baseline_start": "2026-11-12", "baseline_end": "2026-11-12", "baseline_weeks": 1,
            "pct_change": change}


ACT = "ref('fct_github_release_day_activities')"
UNIT_TESTS = [
    {
        "name": "github_headline_is_prs_opened",
        "description": "The headline is PRs opened's change, not an average; the breakdown "
        "spells out every activity.",
        "model": "fct_github_release_day",
        "given": [{"input": ACT, "rows": [
            act("prs_opened", "PRs opened", -10.0), act("prs_merged", "PRs merged", -5.0),
            act("commits", "Commits", 3.0)]}],
        "expect": {"rows": [{"release_day_key": "2026-11-19", "activities_total": 3,
                             "activities_available": 3, "github_release_day_change": -10.0,
                             "breakdown": "PRs opened -10.0% · PRs merged -5.0% · Commits +3.0%"}]},
    },
    {
        "name": "github_headline_stands_when_another_activity_is_missing",
        "description": "A missing commit count does not hide the PRs opened headline.",
        "model": "fct_github_release_day",
        "given": [{"input": ACT, "rows": [
            act("prs_opened", "PRs opened", -10.0), act("commits", "Commits", None)]}],
        "expect": {"rows": [{"activities_available": 1, "github_release_day_change": -10.0,
                             "breakdown": "PRs opened -10.0% · Commits not yet available"}]},
    },
    {
        "name": "github_headline_null_until_prs_opened_counted",
        "description": "Before PRs opened is counted the headline is NULL, whatever else is in.",
        "model": "fct_github_release_day",
        "given": [{"input": ACT, "rows": [
            act("prs_opened", "PRs opened", None), act("commits", "Commits", 3.0)]}],
        "expect": {"rows": [{"github_release_day_change": None}]},
    },
]

doc = yaml.safe_load((ROOT / YML).read_text())
model = doc["models"][0]
model["description"] = ("Metric 4 headline: PRs opened on release day against the Thursday "
                        "before, one row per release day, with its breakdown.")
for col in model["columns"]:
    if col["name"] == "github_release_day_change":
        col["description"] = "PRs opened's release-day change, in percent."
        col["config"]["meta"]["dex"]["null_rule"] = "NULL until PRs opened has a change."
doc["unit_tests"] = UNIT_TESTS
assumptions = [
    {"decision": "What the headline is",
     "chosen": "PRs opened's release-day change (no longer the average of the three)",
     "evidence": "request", "column": "github_release_day_change",
     "detail": "user, 20 Nov: no average, just a headline; PRs opened is the biggest number, "
               "use that one"},
    {"decision": "Another activity not yet available",
     "chosen": "headline still shown; the breakdown says which is missing",
     "evidence": "request", "column": "github_release_day_change",
     "detail": "the headline reads only PRs opened"},
]
model["config"]["meta"]["dex"]["assumptions"] = assumptions

NEVER = {"null_rule": "never"}
count = {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "count",
         **NEVER}
declaration = {
    "model": "fct_github_release_day",
    "description": model["description"],
    "grain": ["release_day_key"],
    "population": {"rule": "One row for the configured release day (var github_release_day)."},
    "columns": {
        "release_day_key": {"role": "key", **NEVER},
        "release_day": {"role": "time", **NEVER},
        "baseline_start": {"role": "attribute", **NEVER},
        "baseline_end": {"role": "attribute", **NEVER},
        "baseline_weeks": {"role": "attribute", **NEVER},
        "activities_total": count,
        "activities_available": count,
        "github_release_day_change": {
            "role": "measure", "aggregation": "max", "additivity": "non_additive",
            "unit": "percent", "null_rule": "NULL until PRs opened has a change."},
        "breakdown": {"role": "attribute", **NEVER},
    },
    "assumptions": assumptions,
}

edits = [
    {"path": "models/marts/fct_github_release_day.sql", "kind": "model_sql", "content": SQL},
    {"path": YML, "kind": "schema_yml",
     "content": yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)},
    {"path": "data_tests/assert_github_release_day_has_breakdown.sql", "kind": "test_sql",
     "content": TEST},
]
(ROOT / ".dex/payloads/29-github-headline.json").write_text(
    json.dumps({"edits": edits, "declarations": [declaration]}, indent=1, ensure_ascii=False)
    + "\n")
print("ok")
