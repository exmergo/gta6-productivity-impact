"""Build .dex/payloads/22-gta-prose.json (seed), 24-gta-prose-models.json (models and tests) and
23-gta-prose-semantic.json: prose says GTA 5 and
GTA 6 (logos keep GTA V and GTA VI). Identifiers (gta_v, file names) are untouched.
Run from the repo root: uv run python .dex/payloads/build_gta_prose.py
"""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def prose(text: str) -> str:
    return re.sub(r"\bGTA V\b", "GTA 5", re.sub(r"\bGTA VI\b", "GTA 6", text))


def files(*globs: str) -> list[str]:
    out = subprocess.run(
        ["git", "grep", "-lE", r"GTA (V|VI)([^a-zA-Z]|$)", "--", *globs],
        cwd=ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    return sorted(out)


KIND = {".csv": "seed_csv", ".sql": "model_sql", ".yml": "schema_yml"}
SEMANTIC = {
    "models/marts/semantic/metrics.yml",
    "models/marts/fct_world_output_semantic.yml",
    "models/marts/fct_world_productivity_semantic.yml",
}
edits, semantic = [], []
for path in files("seeds", "models", "data_tests"):
    text = (ROOT / path).read_text()
    new = prose(text)
    if new == text:
        continue
    kind = "test_sql" if path.startswith("data_tests/") else KIND[Path(path).suffix]
    (semantic if path in SEMANTIC else edits).append({"path": path, "kind": kind if path not in SEMANTIC else "semantic_yml", "content": new})

# Keep the payload copy of the seed (the input the milestone builders read) in step.
src = ROOT / ".dex/payloads/wait_milestones.csv"
src.write_text(prose(src.read_text()))

# Seeds and models go in separate plans: a plan that changes a seed cannot compare its models
# (transform compare: inputs_unsynchronized), and the model edits are meant to be equivalent.
seeds = [e for e in edits if e["path"].startswith("seeds/")]
models = [e for e in edits if not e["path"].startswith("seeds/")]
(ROOT / ".dex/payloads/22-gta-prose.json").write_text(json.dumps({"edits": seeds}, indent=1) + "\n")
(ROOT / ".dex/payloads/24-gta-prose-models.json").write_text(json.dumps({"edits": models}, indent=1) + "\n")
(ROOT / ".dex/payloads/23-gta-prose-semantic.json").write_text(json.dumps({"edits": semantic}, indent=1) + "\n")
print([e["path"] for e in edits], [e["path"] for e in semantic])  # empty once applied
