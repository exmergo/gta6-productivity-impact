"""Replace machine-specific absolute paths in captured Dex envelopes before they are committed.

Usage: uv run python scripts/scrub_evidence.py [files...]   (default: .dex/review/**/*.json)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scrub(text: str) -> str:
    text = text.replace(str(ROOT), ".")
    home = str(Path.home())
    if home not in ("/", ""):
        text = text.replace(home, "~")
    return text


def main(paths: list[str]) -> int:
    files = [Path(p) for p in paths] or sorted((ROOT / ".dex" / "review").rglob("*.json"))
    for path in files:
        original = path.read_text()
        cleaned = scrub(original)
        if cleaned != original:
            path.write_text(cleaned)
            print(f"scrubbed {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
