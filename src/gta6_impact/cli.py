"""gta6: ingest public signals, load the warehouse, build with Dex, draw the charts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from gta6_impact import store, warehouse
from gta6_impact.config import ROOT
from gta6_impact.http import Http

SOURCES = ("wikipedia", "bluesky", "hn", "trends", "reddit")


def ingest(sources: list[str]) -> None:
    http = Http(
        min_interval={
            "api.bsky.app": 0.6,
            "hn.algolia.com": 0.25,
            "arctic-shift.photon-reddit.com": 1.0,
            "wikimedia.org": 0.2,
        }
    )
    pulled = store.pull_id()
    for source in sources:
        if source == "wikipedia":
            from gta6_impact.ingest import wikipedia

            rows = wikipedia.run(http)
        elif source == "bluesky":
            from gta6_impact.ingest import bluesky

            rows = bluesky.run(http, skip=warehouse.settled_keys("bluesky"))
        elif source == "hn":
            from gta6_impact.ingest import hn

            rows = hn.run(http, skip=warehouse.settled_keys("hn"))
        elif source == "reddit":
            from gta6_impact.ingest import reddit

            rows, coverage = reddit.run(http)
            store.write("reddit_coverage", coverage, tag="reddit_coverage", pulled=pulled)
        elif source == "trends":
            from gta6_impact.ingest import trends

            rows = trends.run()
        else:
            raise SystemExit(f"unknown source {source}")
        path = store.write(source, rows, tag=source, pulled=pulled)
        print(json.dumps({"source": source, "rows": len(rows), "path": str(path)}), flush=True)


def dex(*args: str, evidence: str | None = None) -> dict:
    """Run a Dex command and return its JSON envelope. Optionally keep it as evidence."""
    out = subprocess.run(
        [sys.executable, "-m", "exmergo_dex_core", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    envelope = json.loads(out.stdout)
    if evidence:
        path = ROOT / ".dex" / "review" / "refresh" / f"{evidence}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(envelope, indent=1) + "\n"
        text = text.replace(str(ROOT), ".").replace(str(Path.home()), "~")
        path.write_text(text)
    return envelope


def build_and_check() -> None:
    build = dex("transform", "build", "--target", "dev", "--verify", evidence="build")
    completion = build.get("data", {}).get("completion", {})
    print(
        json.dumps(
            {
                "step": "build",
                "status": build["status"],
                "outcome": completion.get("outcome"),
                "blockers": completion.get("blockers"),
            }
        ),
        flush=True,
    )
    if build["status"] != "ok" or completion.get("blockers"):
        raise SystemExit("dex transform build did not complete; see .dex/review/refresh/build.json")
    subprocess.run(
        ["dbt", "parse", "-q"],
        cwd=ROOT,
        check=True,
        env={**__import__("os").environ, "DBT_PROFILES_DIR": str(ROOT)},
    )
    dex("explore", "map", evidence="map")
    check = dex("maintain", "check", evidence="maintain-check")
    data = check.get("data", {})
    print(
        json.dumps(
            {
                "step": "maintain check",
                "status": check["status"],
                "findings": data.get("finding_count", data.get("findings_count")),
            }
        ),
        flush=True,
    )


def charts(png: bool = True) -> None:
    from gta6_impact.charts.build import build
    from gta6_impact.site import build_site

    summary = build(png=png)
    build_site(summary)
    print(json.dumps({"step": "charts", "summary": summary}, default=str), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gta6")
    sub = parser.add_subparsers(dest="command", required=True)
    p_ingest = sub.add_parser("ingest", help="pull public signals into data/raw/")
    p_ingest.add_argument("sources", nargs="*", default=list(SOURCES))
    sub.add_parser("load", help="rebuild raw.* in the DuckDB warehouse from data/raw/")
    p_charts = sub.add_parser("charts", help="draw charts and the site from the semantic layer")
    p_charts.add_argument("--no-png", action="store_true")
    p_refresh = sub.add_parser("refresh", help="ingest, load, build with Dex, check, draw")
    p_refresh.add_argument("sources", nargs="*", default=list(SOURCES))
    p_refresh.add_argument("--offline", action="store_true", help="skip ingest")
    p_refresh.add_argument("--no-png", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "ingest":
        ingest(args.sources)
    elif args.command == "load":
        print(json.dumps(warehouse.load()))
    elif args.command == "charts":
        charts(png=not args.no_png)
    elif args.command == "refresh":
        if not args.offline:
            ingest(args.sources)
        print(json.dumps({"step": "load", "tables": warehouse.load()}), flush=True)
        build_and_check()
        charts(png=not args.no_png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
