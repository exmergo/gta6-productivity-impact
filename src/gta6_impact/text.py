"""Classify a post without keeping it. We store flags and a hash, never the text."""

from __future__ import annotations

import hashlib
import re

from gta6_impact.config import DAY_OFF_PHRASES, GTA_TERMS


def _pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t).replace(r"\ ", r"\s+") for t in terms)
    return re.compile(rf"(?<![\w]){'(?:' + alternation + ')'}(?![\w])", re.IGNORECASE)


DAY_OFF_RE = _pattern(DAY_OFF_PHRASES)
GTA_RE = _pattern(GTA_TERMS)


def mentions_day_off(text: str | None) -> bool:
    return bool(text) and DAY_OFF_RE.search(text) is not None


def mentions_gta(text: str | None) -> bool:
    return bool(text) and GTA_RE.search(text) is not None


def text_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
