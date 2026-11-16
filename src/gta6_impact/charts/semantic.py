"""Chart data comes only from the semantic layer, through `dex explore semantic query`.

If an agent can ask it, the chart can draw it: that is the point of the layer.
"""

from __future__ import annotations

import json
import subprocess
import sys

from gta6_impact.config import ROOT


def query(
    metrics: list[str],
    group_by: list[str] | None = None,
    where: str | None = None,
    order_by: list[str] | None = None,
) -> list[dict]:
    cmd = [
        sys.executable,
        "-m",
        "exmergo_dex_core",
        "explore",
        "semantic",
        "query",
        ",".join(metrics),
        "--limit",
        "5000",
    ]
    if group_by:
        cmd += ["--group-by", ",".join(group_by)]
    if where:
        cmd += ["--where", where]
    if order_by:
        cmd += ["--order-by", ",".join(order_by)]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    envelope = json.loads(out.stdout)
    if envelope.get("status") != "ok":
        raise RuntimeError(f"semantic query failed: {envelope.get('errors')} ({' '.join(cmd)})")
    data = envelope["data"]
    if data.get("truncated"):
        raise RuntimeError(f"semantic query truncated: {' '.join(cmd)}")
    return [dict(zip(data["columns"], row, strict=True)) for row in data["cells"]]
