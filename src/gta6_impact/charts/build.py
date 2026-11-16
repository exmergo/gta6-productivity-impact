"""Draw the charts: semantic queries in, branded HTML cards and PNGs out.

charts/<name>.html is the card (light and dark through ?theme=), charts/png/<name>-<theme>.png
is the capture, and charts/data/<name>.json is exactly what the semantic layer returned.
"""

from __future__ import annotations

import datetime as dt
import json
from html import escape

from gta6_impact.charts.capture import capture
from gta6_impact.charts.semantic import query
from gta6_impact.config import RELEASE_DAY, ROOT

CHARTS = ROOT / "charts"
THEMES = {"light": "dex-site", "dark": "dex-site-dark"}
LOGO = {"dex-site": "dex-logo-black.png", "dex-site-dark": "dex-logo-white.png"}
FOOT_RIGHT = "Built with <b>Dex</b> · trydex.ai"

PAGE = """<!doctype html>
<html lang="en" data-theme="{theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="../brand/dex-site.css">
<link rel="stylesheet" href="../brand/charts.css">
<script>
  const t = new URLSearchParams(location.search).get('theme');
  if (t === 'dark') document.documentElement.dataset.theme = 'dex-site-dark';
</script>
</head>
<body>
<div class="card" style="width:{w}px;height:{h}px">
  <div class="mast">
    <div class="brand"><img alt="Dex" src="../brand/assets/{logo}"></div>
    <div class="meta">{meta}</div>
  </div>
  <div class="main">
{body}
  </div>
  <div class="foot"><span>{source}</span><span>{foot_right}</span></div>
</div>
<script>
  if (document.documentElement.dataset.theme === 'dex-site-dark') {{
    document.querySelector('.brand img').src = '../brand/assets/dex-logo-white.png';
  }}
</script>
</body>
</html>
"""


def _write(
    name: str,
    *,
    title: str,
    meta: str,
    body: str,
    source: str,
    w: int,
    h: int,
    data: dict,
    png: bool,
) -> None:
    CHARTS.mkdir(exist_ok=True)
    (CHARTS / "data").mkdir(exist_ok=True)
    (CHARTS / "data" / f"{name}.json").write_text(json.dumps(data, indent=1, default=str))
    for theme_name, theme in THEMES.items():
        html = PAGE.format(
            theme=theme,
            title=escape(title),
            w=w,
            h=h,
            logo=LOGO[theme],
            meta=escape(meta),
            body=body,
            source=source,
            foot_right=FOOT_RIGHT,
        )
        suffix = "" if theme_name == "light" else "-dark"
        path = CHARTS / f"{name}{suffix}.html"
        path.write_text(html)
        if png:
            capture(path, CHARTS / "png" / f"{name}-{theme_name}.png", w, h)


def _today_meta() -> str:
    days = (RELEASE_DAY - dt.datetime.now(dt.UTC).date()).days
    if days > 0:
        return f"GTA 6 · T-minus {days} day{'s' if days != 1 else ''}"
    if days == 0:
        return "GTA 6 · release day"
    return f"GTA 6 · day +{-days}"


def _day(value: str) -> dt.date:
    return dt.date.fromisoformat(str(value)[:10])


def _span(first_week: dt.date, last_week: dt.date) -> str:
    """Google weeks run Sunday to Saturday; label a window by its first and last day."""
    last_day = last_week + dt.timedelta(days=6)
    if first_week.month == last_day.month:
        return f"{first_week.day}–{last_day.day} {last_day:%b %Y}"
    return f"{first_week.day} {first_week:%b} – {last_day.day} {last_day:%b %Y}"


def index_card(png: bool) -> dict:
    """The Day-Off Index with its breakdown on the same card: never one without the other."""
    window = "day_off_index_window__"
    head = query(
        ["day_off_index"],
        [
            f"{window}breakdown",
            f"{window}current_start_week",
            f"{window}current_end_week",
            f"{window}prior_start_week",
            f"{window}prior_end_week",
        ],
    )[0]
    terms = query(
        ["day_off_index_term_change", "day_off_index_term_current", "day_off_index_term_prior"],
        ["day_off_index_term__term"],
    )
    current = _span(
        _day(head[f"{window}current_start_week__day"]), _day(head[f"{window}current_end_week__day"])
    )
    prior = _span(
        _day(head[f"{window}prior_start_week__day"]), _day(head[f"{window}prior_end_week__day"])
    )
    index = head["day_off_index"]
    big = f"{index:+.0f}<small>%</small>" if index is not None else "n/a"
    rows = []
    for r in sorted(terms, key=lambda r: -(r["day_off_index_term_change"] or 0)):
        change = r["day_off_index_term_change"]
        cell = f'<b class="red">{change:+.0f}%</b>' if change is not None else "<b>n/a</b>"
        rows.append(
            f'<div class="row"><span>“{escape(r["day_off_index_term__term"])}”'
            f" · {r['day_off_index_term_prior']:.1f} → {r['day_off_index_term_current']:.1f}"
            f"</span>{cell}</div>"
        )
    index_cell = f'<b class="red">{index:+.0f}%</b>' if index is not None else "<b>n/a</b>"
    body = f"""    <div class="hero">
      <div>
        <div class="big">{big}</div>
        <h1 style="margin-top:22px">US Google searches for skipping work, vs last year.</h1>
        <p class="lede">The Day-Off Index: the average change in searches for “call in sick”,
        “sick day” and “day off work”, {escape(current)} against {escape(prior)}.
        GTA 6 launches Thursday 19 November.</p>
      </div>
      <div class="box">
        <div class="strip">Breakdown · 2025 → 2026</div>
        <div class="rows">
          {"".join(rows)}
          <div class="row"><span>Day-Off Index (average)</span>{index_cell}</div>
        </div>
      </div>
    </div>"""
    data = {
        "day_off_index": index,
        "breakdown": head[f"{window}breakdown"],
        "current_window": current,
        "prior_window": prior,
        "terms": terms,
    }
    _write(
        "day-off-index",
        title="Day-Off Index",
        meta=_today_meta(),
        body=body,
        source="Google Trends · US · weekly, one request per phrase across both years · "
        "search interest, not headcount",
        w=1200,
        h=630,
        data=data,
        png=png,
    )
    return data


def build(png: bool = True) -> dict:
    return index_card(png)


if __name__ == "__main__":
    print(json.dumps(build(), default=str))
