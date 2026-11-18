"""Build .dex/payloads/21-milestone-labels.json: two chart labels reworded (user request).
Run from the repo root: uv run python .dex/payloads/build_milestone_labels.py
"""

import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_IN = ROOT / ".dex/payloads/wait_milestones.csv"
LABELS = {
    "covid_vaccine": "COVID-19 vaccine in under a year",
    "artemis_ii_flyby": "Artemis II, humans back to the Moon",
}

rows = list(csv.DictReader(CSV_IN.open()))
fields = list(rows[0])
for r in rows:
    r["chart_label"] = LABELS.get(r["milestone_id"], r["chart_label"])
assert sum(r["chart_label"] in LABELS.values() for r in rows) == len(LABELS)
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
w.writeheader()
w.writerows(rows)
CSV_IN.write_text(buf.getvalue())
(ROOT / ".dex/payloads/21-milestone-labels.json").write_text(
    json.dumps({"edits": [{"path": "seeds/wait_milestones.csv", "kind": "seed_csv", "content": buf.getvalue()}]}, indent=1)
    + "\n"
)
print("ok")
