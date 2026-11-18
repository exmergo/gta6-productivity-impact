"""Build .dex/payloads/17-world-output-semantic.json and 18-world-output-metrics.json: Metric 3's
semantic models (the daily wait and its milestones) and its governed metrics.
The derived proposal on the model plan failed to parse (review 73: output_day used as both
entity and dimension), so the semantic models are authored here with a distinct entity name.
Run from the repo root: uv run python .dex/payloads/build_world_output_semantic.py
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CAVEAT = "Constant 2015 US$; 2026 is an IMF-based estimate; never add cumulative output across days."


def meta(**dex):
    return {"config": {"meta": {"dex": dex}}}


SEMANTIC = {
    "version": 2,
    "semantic_models": [
        {
            "name": "fct_world_output_daily",
            "description": (
                "Metric 3, everything humanity made while waiting for GTA 6: world real output on "
                "each UTC day from GTA V's release (2013-09-17) to the day before GTA 6's "
                "(2026-11-18), and the running total since GTA V. One row per day. " + CAVEAT
            ),
            "model": "ref('fct_world_output_daily')",
            "defaults": {"agg_time_dimension": "output_day"},
            "entities": [
                {"name": "world_output_day", "type": "primary", "expr": "output_day", **meta(null_rule="never")}
            ],
            "dimensions": [
                {
                    "name": "output_day",
                    "type": "time",
                    "type_params": {"time_granularity": "day"},
                    "description": "UTC day of the wait.",
                    **meta(null_rule="never"),
                },
                {"name": "data_year", "type": "categorical", "description": "Calendar year of the day."},
                {
                    "name": "is_estimate",
                    "type": "categorical",
                    "description": "True when the day's year is carried by IMF growth (2026).",
                },
            ],
            "measures": [
                {
                    "name": "daily_output",
                    "agg": "sum",
                    "expr": "daily_output",
                    "description": "World real output made on the day, constant 2015 US$ (the year spread evenly).",
                    **meta(unit="currency:USD", additivity="additive", null_rule="NULL when the year's output is unavailable."),
                },
                {
                    "name": "cumulative_output",
                    "agg": "max",
                    "expr": "cumulative_output",
                    "description": "Running total of world real output since GTA V's release, through the day. Never sum it across days.",
                    "non_additive_dimension": {"name": "output_day", "window_choice": "max"},
                    **meta(unit="currency:USD", additivity="semi_additive", null_rule="NULL from the first unavailable day on."),
                },
            ],
        },
        {
            "name": "fct_wait_milestones",
            "description": (
                "Metric 3: the milestones of the wait between GTA V and GTA 6 (editorial picks, one "
                "public source each), each with the world real output made since GTA V by the day "
                "before it. One row per milestone. " + CAVEAT
            ),
            "model": "ref('fct_wait_milestones')",
            "defaults": {"agg_time_dimension": "event_date"},
            "entities": [
                {"name": "milestone", "type": "primary", "expr": "milestone_id", **meta(null_rule="never")}
            ],
            "dimensions": [
                {
                    "name": "event_date",
                    "type": "time",
                    "type_params": {"time_granularity": "day"},
                    "description": "UTC day of the event.",
                },
                {"name": "milestone_id", "type": "categorical", "description": "Slug."},
                {"name": "title", "type": "categorical", "description": "What happened."},
                {"name": "chart_label", "type": "categorical", "description": "Short label for the chart."},
                {"name": "category", "type": "categorical", "description": "Theme; rockstar marks the Rockstar nods."},
                {"name": "tier", "type": "categorical", "description": "anchor, hero (on the chart) or long (site table only)."},
                {"name": "date_precision", "type": "categorical", "description": "day, or month."},
                {"name": "source_url", "type": "categorical", "description": "One public source for the date."},
            ],
            "measures": [
                {
                    "name": "output_by_then",
                    "agg": "max",
                    "expr": "output_by_then",
                    "description": "World real output made from GTA V's release through the day before the event, constant 2015 US$.",
                    **meta(unit="currency:USD", additivity="semi_additive", null_rule="NULL outside the wait."),
                },
                {
                    "name": "share_of_wait_output",
                    "agg": "max",
                    "expr": "share_of_wait_output",
                    "description": "output_by_then over the whole wait's output (0 to 1).",
                    **meta(unit="fraction", additivity="non_additive"),
                },
                {
                    "name": "days_to_gta_6",
                    "agg": "max",
                    "expr": "days_to_gta_6",
                    "description": "Days from the event to GTA 6's release day.",
                    **meta(unit="days", additivity="non_additive"),
                },
            ],
        },
    ],
}

METRICS = [
    {
        "name": "world_output_produced",
        "label": "World output made while waiting for GTA 6",
        "description": (
            "Metric 3, everything humanity made while waiting for GTA 6. World real output (World "
            "Bank NY.GDP.MKTP.KD) made over the days asked for. With no group-by it is the headline: "
            "everything made from GTA V's release (17 Sep 2013) to the day before GTA 6 (18 Nov "
            "2026), 4,811 days. " + CAVEAT
        ),
        "type": "simple",
        "type_params": {"measure": "daily_output"},
    },
    {
        "name": "world_output_cumulative",
        "label": "World output since GTA V, running total",
        "description": (
            "Metric 3. Running total of world real output since GTA V's release, as of each day. "
            "Group by world_output_day__output_day or metric_time; at week or month grain it reads the "
            "period's last day. " + CAVEAT
        ),
        "type": "simple",
        "type_params": {"measure": "cumulative_output"},
    },
    {
        "name": "world_output_per_second",
        "label": "World output per second",
        "description": (
            "Metric 3. The rate the world makes things at: one day's world real output / 86,400. "
            "Only meaningful by day: group by world_output_day__output_day (or metric_time__day). "
            "A yearly average spread evenly; nobody measures GDP by the second. " + CAVEAT
        ),
        "type": "derived",
        "type_params": {"expr": "world_output_produced / 86400", "metrics": [{"name": "world_output_produced"}]},
    },
    {
        "name": "wait_milestone_output",
        "label": "World output made by each milestone",
        "description": (
            "Metric 3. World real output made since GTA V's release by the day before each milestone. "
            "Group by milestone__title and milestone__event_date (milestone__tier = 'hero' for the "
            "chart). Milestones are editorial picks, not a ranking. " + CAVEAT
        ),
        "type": "simple",
        "type_params": {"measure": "output_by_then"},
    },
    {
        "name": "wait_milestone_share",
        "label": "Share of the wait's output made by each milestone",
        "description": "Metric 3. wait_milestone_output over the whole wait's output (0 to 1). Group by milestone.",
        "type": "simple",
        "type_params": {"measure": "share_of_wait_output"},
    },
    {
        "name": "wait_milestone_days_to_gta_6",
        "label": "Days from each milestone to GTA 6",
        "description": "Metric 3. Days from the milestone to GTA 6's release day (19 Nov 2026). Group by milestone.",
        "type": "simple",
        "type_params": {"measure": "days_to_gta_6"},
    },
]


def dump(doc):
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


(ROOT / ".dex/payloads/17-world-output-semantic.json").write_text(
    json.dumps(
        {"edits": [{"path": "models/marts/fct_world_output_semantic.yml", "kind": "semantic_yml", "content": dump(SEMANTIC)}]},
        indent=1,
    )
    + "\n"
)
(ROOT / ".dex/payloads/18-world-output-metrics.json").write_text(
    json.dumps(
        {"definitions": [{"kind": "metric", "path": "models/marts/semantic/metrics.yml", "content": dump(m)} for m in METRICS]},
        indent=1,
    )
    + "\n"
)
print("ok")
