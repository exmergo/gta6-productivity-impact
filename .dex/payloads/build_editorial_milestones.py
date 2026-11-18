"""Build .dex/payloads/19-editorial-milestones.json and 20-editorial-milestones-semantic.json:
Metric 3's editorial cut. The seed gains is_editorial (the milestones the chart draws) and a
Claude Code row; fct_wait_milestones passes the flag through; the semantic model exposes it
as milestone__is_editorial so the chart filters on it instead of a hard-coded list.
Run from the repo root: uv run python .dex/payloads/build_editorial_milestones.py
"""

import csv
import io
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PAYLOADS = ROOT / ".dex/payloads"
CSV_IN = PAYLOADS / "wait_milestones.csv"

EDITORIAL = {
    "comet_landing",
    "alphago",
    "red_dead_redemption_2",
    "black_hole_image",
    "covid_vaccine",
    "chatgpt",
    "gta_vi_trailer_1",
    "claude_code",
    "artemis_ii_flyby",
}
CLAUDE_CODE = {
    "milestone_id": "claude_code",
    "event_date": "2025-02-24",
    "date_precision": "day",
    "category": "ai",
    "tier": "hero",
    "title": "Claude Code released (research preview)",
    "chart_label": "Claude Code",
    "why": "An AI coding agent in the terminal; shipped beside Claude 3.7 Sonnet, generally available 2025-05-22",
    "source_url": "https://www.anthropic.com/news/claude-3-7-sonnet",
}


def dump(doc):
    return yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


# ---------------------------------------------------------------- seed
rows = list(csv.DictReader(CSV_IN.open()))
if not any(r["milestone_id"] == "claude_code" for r in rows):
    rows.append(dict(CLAUDE_CODE))
rows.sort(key=lambda r: (r["event_date"], r["milestone_id"]))
fields = [
    "milestone_id",
    "event_date",
    "date_precision",
    "category",
    "tier",
    "is_editorial",
    "title",
    "chart_label",
    "why",
    "source_url",
]
for r in rows:
    r["is_editorial"] = "true" if r["milestone_id"] in EDITORIAL else "false"
assert {r["milestone_id"] for r in rows if r["is_editorial"] == "true"} == EDITORIAL
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
w.writeheader()
w.writerows({k: r[k] for k in fields} for r in rows)
SEED = buf.getvalue()
CSV_IN.write_text(SEED)

seed_yml = yaml.safe_load((ROOT / "seeds/wait_milestones.yml").read_text())
seed = seed_yml["seeds"][0]
seed["description"] = (
    "Metric 3: moments between GTA V and GTA 6, one row per milestone, each dated to a UTC day "
    "and carrying one public source. is_editorial marks the ones the chart draws."
)
seed["config"]["column_types"]["is_editorial"] = "boolean"
cols = [c for c in seed["columns"] if c["name"] != "is_editorial"]
for c in cols:
    if c["name"] == "tier":
        c["description"] = "anchor (the two releases), hero (headline moments) or long."
at = next(i for i, c in enumerate(cols) if c["name"] == "tier") + 1
cols.insert(
    at,
    {
        "name": "is_editorial",
        "description": "True for the editorial milestones: the ones drawn on the Metric 3 chart.",
        "data_tests": ["not_null"],
    },
)
seed["columns"] = cols

# ---------------------------------------------------------------- mart
MILES_SQL = (ROOT / "models/marts/fct_wait_milestones.sql").read_text()
if "milestones.is_editorial" not in MILES_SQL:
    MILES_SQL = MILES_SQL.replace(
        "    milestones.tier,\n", "    milestones.tier,\n    milestones.is_editorial,\n", 1
    )
assert "milestones.is_editorial" in MILES_SQL

# The declaration, read back from the model's YAML (Dex rendered it there) and extended.
model = yaml.safe_load((ROOT / "models/marts/fct_wait_milestones.yml").read_text())["models"][0]
dex = model["config"]["meta"]["dex"]
columns = {}
for c in model["columns"]:
    spec = dict(c["config"]["meta"]["dex"])
    if c.get("description"):
        spec["description"] = c["description"]
    columns[c["name"]] = spec
    if c["name"] == "tier":
        spec["description"] = "anchor (the two releases), hero (headline moments) or long."
        columns["is_editorial"] = {
            "role": "dimension",
            "null_rule": "never",
            "description": "True for the editorial milestones: the ones drawn on the Metric 3 chart.",
        }
MILES_DECL = {
    "model": "fct_wait_milestones",
    "description": model["description"],
    "grain": dex["grain"],
    "population": dex["population"],
    "columns": columns,
    "assumptions": dex["assumptions"]
    + [
        {
            "decision": "Which milestones the chart draws",
            "chosen": "the nine flagged is_editorial: comet, AlphaGo, RDR2, black hole, vaccine, "
            "ChatGPT, GTA VI trailer, Claude Code, Artemis II",
            "evidence": "request",
            "column": "is_editorial",
            "detail": "user named the milestones to keep on the chart and asked for Claude Code",
        },
        {
            "decision": "Claude Code's date",
            "chosen": "2025-02-24, the research-preview launch beside Claude 3.7 Sonnet",
            "evidence": "default",
            "column": "milestone_id",
            "detail": "first public release; general availability (2025-05-22) is kept in why",
        },
    ],
}

(PAYLOADS / "19-editorial-milestones.json").write_text(
    json.dumps(
        {
            "edits": [
                {"path": "seeds/wait_milestones.csv", "kind": "seed_csv", "content": SEED},
                {"path": "seeds/wait_milestones.yml", "kind": "schema_yml", "content": dump(seed_yml)},
                {"path": "models/marts/fct_wait_milestones.sql", "kind": "model_sql", "content": MILES_SQL},
            ],
            "declarations": [MILES_DECL],
        },
        indent=1,
    )
    + "\n"
)

# ---------------------------------------------------------------- semantic layer
sem_path = "models/marts/fct_world_output_semantic.yml"
sem = yaml.safe_load((ROOT / sem_path).read_text())
miles = next(m for m in sem["semantic_models"] if m["name"] == "fct_wait_milestones")
dims = [d for d in miles["dimensions"] if d["name"] != "is_editorial"]
for d in dims:
    if d["name"] == "tier":
        d["description"] = "anchor (the two releases), hero (headline moments) or long."
at = next(i for i, d in enumerate(dims) if d["name"] == "tier") + 1
dims.insert(
    at,
    {
        "name": "is_editorial",
        "type": "categorical",
        "description": "True for the editorial milestones, the ones the Metric 3 chart draws.",
    },
)
miles["dimensions"] = dims

met_path = "models/marts/semantic/metrics.yml"
met_text = (ROOT / met_path).read_text()
met_text = met_text.replace(
    "(milestone__tier = 'hero' for the chart)", "(milestone__is_editorial = true for the chart)"
).replace(
    "    Group by milestone__title and milestone__event_date (milestone__tier = 'hero' for the chart). Milestones\n"
    "    are editorial picks, not a ranking.",
    "    Group by milestone__title and milestone__event_date; filter milestone__is_editorial = true for the\n"
    "    chart's milestones.",
)
assert "is_editorial" in met_text

(PAYLOADS / "20-editorial-milestones-semantic.json").write_text(
    json.dumps(
        {
            "edits": [
                {"path": sem_path, "kind": "semantic_yml", "content": dump(sem)},
                {"path": met_path, "kind": "semantic_yml", "content": met_text},
            ]
        },
        indent=1,
    )
    + "\n"
)
print("ok")
