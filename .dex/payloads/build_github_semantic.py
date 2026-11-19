"""Build .dex/payloads/26-github-semantic.json and 27-github-metrics.json: Metric 4's semantic
models and metrics. Run from the repo root: uv run python .dex/payloads/build_github_semantic.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NEVER = {"meta": {"dex": {"null_rule": "never"}}}


def dim(name: str, description: str, time: bool = False) -> dict:
    d = {"name": name, "type": "time" if time else "categorical", "description": description}
    if time:
        d["type_params"] = {"time_granularity": "day"}
    d["config"] = NEVER
    return d


def measure(name: str, agg: str, expr: str, description: str, unit: str, additivity: str,
            null_rule: str) -> dict:
    return {
        "name": name,
        "agg": agg,
        "expr": expr,
        "description": description,
        "config": {"meta": {"dex": {"unit": unit, "additivity": additivity,
                                    "null_rule": null_rule}}},
    }


semantic = {
    "version": 2,
    "semantic_models": [
        {
            "name": "fct_github_daily",
            "description": "Metric 4: GitHub activity per UTC day (PRs opened, PRs merged, "
            "commits), one row per day per activity. Never add counts across activities.",
            "model": "ref('fct_github_daily')",
            "defaults": {"agg_time_dimension": "activity_date"},
            "entities": [
                {"name": "github_day", "type": "primary", "expr": "github_day_key",
                 "config": NEVER}
            ],
            "dimensions": [
                dim("activity_date", "UTC day.", time=True),
                dim("activity", "prs_opened, prs_merged or commits."),
                dim("activity_label", "PRs opened, PRs merged or Commits."),
                dim("weekday_name", "Day of the week."),
                dim("is_release_day", "True on GTA 6's release day."),
                dim("days_from_release", "Days after release day (negative before)."),
            ],
            "measures": [
                measure("github_activity_count_measure", "sum", "activity_count",
                        "How many on the day (GitHub Search API total_count).", "count",
                        "additive", "NULL when unavailable, never zero.")
            ],
        },
        {
            "name": "fct_github_release_day_activities",
            "description": "Metric 4 breakdown: one row per activity, release day against the "
            "same weekday a week before (a median over the weeks when more than one).",
            "model": "ref('fct_github_release_day_activities')",
            "defaults": {"agg_time_dimension": "release_day"},
            "entities": [
                {"name": "github_activity", "type": "primary", "expr": "activity",
                 "config": NEVER}
            ],
            "dimensions": [
                dim("activity", "prs_opened, prs_merged or commits."),
                dim("activity_label", "PRs opened, PRs merged or Commits."),
                dim("release_day", "GTA 6's release day.", time=True),
                dim("baseline_start", "First baseline day.", time=True),
                dim("baseline_end", "Last baseline day.", time=True),
            ],
            "measures": [
                measure("github_activity_pct_change", "max", "pct_change",
                        "Release day against the baseline average, in percent.", "percent",
                        "non_additive",
                        "NULL unless release day and every baseline day have a count."),
                measure("github_activity_release_day_count", "max", "release_day_count",
                        "Count on release day.", "count", "non_additive",
                        "NULL until release day has ended and been counted."),
                measure("github_activity_baseline_count", "max", "baseline_count",
                        "Count on the baseline day (median over baseline days).", "count",
                        "non_additive",
                        "NULL when no baseline day has a count."),
            ],
        },
        {
            "name": "fct_github_release_day",
            "description": "Metric 4 headline: the average of the activities' release-day "
            "changes, one row per release day, with its breakdown.",
            "model": "ref('fct_github_release_day')",
            "defaults": {"agg_time_dimension": "release_day"},
            "entities": [
                {"name": "github_release_day", "type": "primary", "expr": "release_day_key",
                 "config": NEVER}
            ],
            "dimensions": [
                dim("breakdown", "Every activity's change. Always report it with the headline."),
                dim("release_day", "GTA 6's release day.", time=True),
                dim("baseline_start", "First baseline day.", time=True),
                dim("baseline_end", "Last baseline day.", time=True),
            ],
            "measures": [
                measure("github_release_day_change_measure", "max",
                        "github_release_day_change",
                        "Average of the activities' release-day changes, in percent.",
                        "percent", "non_additive", "NULL until every activity has a change."),
            ],
        },
    ],
}

# One file per mart, beside it, as Dex derived them: keep the population and assumptions Dex
# carried over from the declarations (config.meta.dex), replace the rest with stable names.
edits = []
for sm in semantic["semantic_models"]:
    path = f"models/marts/{sm['name']}_semantic.yml"
    derived = ROOT / path
    if derived.exists():
        old = yaml.safe_load(derived.read_text())["semantic_models"][0]
        if "config" in old:
            sm["config"] = old["config"]
    edits.append(
        {
            "path": path,
            "kind": "semantic_yml",
            "content": yaml.safe_dump(
                {"version": 2, "semantic_models": [sm]}, sort_keys=False, width=100
            ),
        }
    )
(ROOT / ".dex/payloads/26-github-semantic.json").write_text(
    json.dumps({"edits": edits}, indent=1) + "\n"
)

METRICS = [
    {
        "name": "github_release_day_change",
        "label": "GitHub on GTA 6 release day",
        "description": "Metric 4. Average change, in percent, of PRs opened, PRs merged and "
        "commits on GitHub on GTA 6's release day (Thu 19 Nov 2026, UTC) against the Thursday "
        "before (12 Nov 2026). -5 = GitHub 5% quieter. Never report it "
        "alone: always with its breakdown (group by github_release_day__breakdown, or query "
        "github_activity_change by github_activity__activity).",
        "type": "simple",
        "type_params": {"measure": "github_release_day_change_measure"},
    },
    {
        "name": "github_activity_change",
        "label": "GitHub release day, change by activity",
        "description": "Metric 4 breakdown: one activity's release-day count against the "
        "same weekday a week before, in percent. Group by "
        "github_activity__activity.",
        "type": "simple",
        "type_params": {"measure": "github_activity_pct_change"},
    },
    {
        "name": "github_activity_release_day",
        "label": "GitHub activity on release day",
        "description": "Metric 4. An activity's count on release day (UTC). Group by "
        "github_activity__activity.",
        "type": "simple",
        "type_params": {"measure": "github_activity_release_day_count"},
    },
    {
        "name": "github_activity_baseline",
        "label": "GitHub activity on a normal day",
        "description": "Metric 4. An activity's count on the same weekday a week before release "
        "day (the median when the baseline spans more weeks). Group by "
        "github_activity__activity.",
        "type": "simple",
        "type_params": {"measure": "github_activity_baseline_count"},
    },
    {
        "name": "github_activity_count",
        "label": "GitHub activity per day",
        "description": "Metrics 4 and 6. PRs opened, PRs merged or commits on GitHub per UTC "
        "day (GitHub Search API total_count). Always group by github_day__activity: never add "
        "across activities. NULL is unavailable, never zero.",
        "type": "simple",
        "type_params": {"measure": "github_activity_count_measure"},
    },
]

(ROOT / ".dex/payloads/27-github-metrics.json").write_text(
    json.dumps(
        {
            "definitions": [
                {
                    "kind": "metric",
                    "path": "models/marts/semantic/metrics.yml",
                    "content": yaml.safe_dump(m, sort_keys=False, width=100),
                }
                for m in METRICS
            ]
        },
        indent=1,
    )
    + "\n"
)
print("ok")
