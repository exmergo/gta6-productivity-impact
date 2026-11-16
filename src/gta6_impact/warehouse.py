"""Rebuild the raw schema from every landed Parquet file. Same files in, same tables out."""

from __future__ import annotations

import datetime as dt

import duckdb

from gta6_impact.config import MANUAL_DIR, RAW_DIR, WAREHOUSE

# source folder -> (raw table, dedupe key, ordering that wins)
TABLES = {
    "bluesky": ("bluesky_daily_hits", "day, seed, gta_filter", "pull_id desc"),
    "hn": ("hn_daily_hits", "day, seed, gta_filter", "pull_id desc"),
    "wikipedia": ("wiki_pageviews", "article, granularity, ts", "pull_id desc"),
    "trends": ("trends_interest", "request_id, geo, term, day", "pull_id desc"),
}


def load() -> dict[str, int]:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    with duckdb.connect(str(WAREHOUSE)) as con:
        con.execute("set TimeZone = 'UTC'")
        con.execute("create schema if not exists raw")
        for folder, (table, key, order) in TABLES.items():
            files = sorted((RAW_DIR / folder).glob("*.parquet"))
            manual = sorted((MANUAL_DIR / folder).glob("*.parquet")) if folder == "trends" else []
            paths = [str(p) for p in files + manual]
            if not paths:
                continue
            con.execute(
                f"""
                create or replace table raw.{table} as
                select * exclude (rn) from (
                    select *, row_number() over (partition by {key} order by {order}) as rn
                    from read_parquet(?, union_by_name = true)
                ) where rn = 1
                """,
                [paths],
            )
            counts[table] = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
    return counts


def settled_keys(folder: str, settle_days: int = 3) -> set[tuple]:
    """Daily counts older than a few days rarely move; skip re-asking for them."""
    files = sorted((RAW_DIR / folder).glob("*.parquet"))
    if not files:
        return set()
    cutoff = dt.datetime.now(dt.UTC).date() - dt.timedelta(days=settle_days)
    rows = duckdb.sql(
        "select distinct day, seed, gta_filter from read_parquet(?, union_by_name = true) "
        "where hits_total is not null and day < ?",
        params=[[str(p) for p in files], cutoff],
    ).fetchall()
    return {(r[0], r[1], r[2]) for r in rows}
