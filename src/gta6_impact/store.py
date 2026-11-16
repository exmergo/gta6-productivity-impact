"""Landing zone: every pull is an immutable Parquet file under data/raw/<source>/."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from gta6_impact.config import RAW_DIR


def pull_id() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def write(source: str, rows: list[dict], tag: str, pulled: str) -> Path | None:
    if not rows:
        return None
    directory = RAW_DIR / source
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{pulled}__{tag}.parquet"
    for row in rows:
        row["pull_id"] = pulled
    pq.write_table(pa.Table.from_pylist(rows), path, compression="zstd")
    return path
