"""Headless Chrome screenshots of the chart pages. Same idea as the brand repo's capture.sh."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

CANDIDATES = (
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)


def chrome() -> str:
    for candidate in CANDIDATES:
        if not candidate:
            continue
        found = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if found:
            return found
    raise RuntimeError("No Chrome or Chromium found. Set CHROME=/path/to/chrome.")


def capture(html: Path, png: Path, width: int, height: int, scale: int = 2) -> Path:
    png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            chrome(),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-sandbox",
            "--allow-file-access-from-files",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale}",
            "--virtual-time-budget=5000",
            f"--screenshot={png}",
            html.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    return png
