"""Build .dex/payloads/39-producthunt-semantic.json (semantic models) and
40-producthunt-metrics.json (metrics) for Metric 5, mirroring Metric 4's.
Run from the repo root: uv run python .dex/payloads/build_producthunt_semantic.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NEVER = {"meta": {"dex": {"null_rule": "never"}}}


def dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


def measure(name, expr, agg, description, unit, additivity, null_rule):
    return {
        "name": name,
        "agg": agg,
        "expr": expr,
        "description": description,
        "config": {"meta": {"dex": {"unit": unit, "additivity": additivity, "null_rule": null_rule}}},
    }


def dim(name, description, time=False):
    d = {"name": name, "type": "time" if time else "categorical", "description": description}
    if time:
        d["type_params"] = {"time_granularity": "day"}
    d["config"] = NEVER
    return d


ACT = "launches or comments."
ACT_LABEL = "Launches or Comments."

daily = {
    "name": "fct_producthunt_daily",
    "description": "Metric 5: Product Hunt activity per Pacific day (launches, launch-day "
    "comments), one row per day per activity. Never add counts across activities.",
    "model": "ref('fct_producthunt_daily')",
    "defaults": {"agg_time_dimension": "launch_day"},
    "entities": [
        {"name": "producthunt_day", "type": "primary", "expr": "producthunt_day_key", "config": NEVER}
    ],
    "dimensions": [
        dim("launch_day", "Pacific day (Product Hunt's day).", time=True),
        dim("activity", ACT),
        dim("activity_label", ACT_LABEL),
        dim("is_release_day", "True on GTA 6's release day."),
        dim("days_from_release", "Days after release day (negative before)."),
    ],
    "measures": [
        measure("producthunt_activity_count_measure", "activity_count", "sum",
                "How many on the day.", "count", "additive", "NULL when unavailable, never zero."),
        measure("producthunt_activity_wow_pct_change", "wow_pct_change", "max",
                "The day against the same weekday a week earlier, in percent.", "percent",
                "non_additive", "NULL unless both days have a count."),
        measure("producthunt_activity_prior_week_count", "prior_week_count", "max",
                "The same weekday a week earlier.", "count", "non_additive",
                "NULL when that day has no count."),
    ],
}

activities = {
    "name": "fct_producthunt_release_day_activities",
    "description": "Metric 5 breakdown: one row per activity, release day against the same "
    "weekday a week before.",
    "model": "ref('fct_producthunt_release_day_activities')",
    "defaults": {"agg_time_dimension": "release_day"},
    "entities": [
        {"name": "producthunt_activity", "type": "primary", "expr": "activity", "config": NEVER}
    ],
    "dimensions": [
        dim("activity", ACT),
        dim("activity_label", ACT_LABEL),
        dim("release_day", "GTA 6's release day.", time=True),
        dim("baseline_start", "First baseline day.", time=True),
        dim("baseline_end", "Last baseline day.", time=True),
    ],
    "measures": [
        measure("producthunt_activity_pct_change", "pct_change", "max",
                "Release day against the baseline, in percent.", "percent", "non_additive",
                "NULL unless release day and every baseline day have a count."),
        measure("producthunt_activity_release_day_count", "release_day_count", "max",
                "Count on release day.", "count", "non_additive",
                "NULL until release day has ended and been counted."),
        measure("producthunt_activity_baseline_count", "baseline_count", "max",
                "Count on the baseline day (median over baseline days).", "count",
                "non_additive", "NULL when no baseline day has a count."),
    ],
}

headline = {
    "name": "fct_producthunt_release_day",
    "description": "Metric 5 headline: launches and launch-day comments on release day against "
    "the Thursday before, one row per release day, with its breakdown.",
    "model": "ref('fct_producthunt_release_day')",
    "defaults": {"agg_time_dimension": "release_day"},
    "entities": [
        {"name": "producthunt_release_day", "type": "primary", "expr": "release_day_key",
         "config": NEVER}
    ],
    "dimensions": [
        dim("breakdown", "Both activities' changes. Report it with the headline."),
        dim("release_day", "GTA 6's release day.", time=True),
        dim("baseline_start", "First baseline day.", time=True),
        dim("baseline_end", "Last baseline day.", time=True),
    ],
    "measures": [
        measure("producthunt_launches_change_measure", "producthunt_launches_change", "max",
                "Launches' release-day change, in percent.", "percent", "non_additive",
                "NULL until launches have a change."),
        measure("producthunt_comments_change_measure", "producthunt_comments_change", "max",
                "Launch-day comments' release-day change, in percent.", "percent",
                "non_additive", "NULL until comments have a change."),
    ],
}

edits = [
    {
        "path": f"models/marts/{sm['name']}_semantic.yml",
        "kind": "semantic_yml",
        "content": dump({"version": 2, "semantic_models": [sm]}),
    }
    for sm in (daily, activities, headline)
]
(ROOT / ".dex/payloads/39-producthunt-semantic.json").write_text(
    json.dumps({"edits": edits}, indent=1) + "\n"
)

WINDOW = ("GTA 6's release day (Thu 19 Nov 2026, a Pacific day, Product Hunt's own) against the "
          "Thursday before (12 Nov 2026)")
METRICS = [
    ("producthunt_launches_change", "Product Hunt on GTA 6 release day: launches",
     f"Metric 5 headline. Change, in percent, of products launched on Product Hunt on {WINDOW}. "
     "Every launch counts, featured or not (the API's own count for the day). Report it with "
     "producthunt_comments_change, or group by producthunt_release_day__breakdown.",
     "producthunt_launches_change_measure"),
    ("producthunt_comments_change", "Product Hunt on GTA 6 release day: comments",
     f"Metric 5 headline. Change, in percent, of comments on Product Hunt launches on {WINDOW}: "
     "top-level comments written during the launch day on that day's launches (replies left "
     "out), so both days are counted at the same age. Report it with "
     "producthunt_launches_change.",
     "producthunt_comments_change_measure"),
    ("producthunt_activity_change", "Product Hunt release day, change by activity",
     "Metric 5 breakdown: one activity's release-day count against the same weekday a week "
     "before, in percent. Group by producthunt_activity__activity.",
     "producthunt_activity_pct_change"),
    ("producthunt_activity_release_day", "Product Hunt activity on release day",
     "Metric 5. An activity's count on release day (Pacific). Group by "
     "producthunt_activity__activity.",
     "producthunt_activity_release_day_count"),
    ("producthunt_activity_baseline", "Product Hunt activity on a normal day",
     "Metric 5. An activity's count on the same weekday a week before release day. Group by "
     "producthunt_activity__activity.",
     "producthunt_activity_baseline_count"),
    ("producthunt_activity_count", "Product Hunt activity per day",
     "Metric 5. Launches, or launch-day top-level comments on that day's launches, per Pacific "
     "day. Always group by producthunt_day__activity: never add across activities. NULL is "
     "unavailable, never zero.",
     "producthunt_activity_count_measure"),
    ("producthunt_activity_change_wow", "Product Hunt activity, change on the same weekday a week earlier",
     "Metric 5. A day's count against the same weekday 7 days earlier, in percent, per activity. "
     "Group by metric_time__day and producthunt_day__activity. NULL when either day is missing.",
     "producthunt_activity_wow_pct_change"),
    ("producthunt_activity_count_week_before", "Product Hunt activity, same weekday a week earlier",
     "Metric 5. The count on the same weekday 7 days earlier, per activity. Group by "
     "metric_time__day and producthunt_day__activity.",
     "producthunt_activity_prior_week_count"),
]
definitions = [
    {
        "kind": "metric",
        "path": "models/marts/semantic/metrics.yml",
        "content": dump({"name": n, "label": label, "description": d, "type": "simple",
                         "type_params": {"measure": m}}),
    }
    for n, label, d, m in METRICS
]
(ROOT / ".dex/payloads/40-producthunt-metrics.json").write_text(
    json.dumps({"definitions": definitions}, indent=1) + "\n"
)
print("ok")
