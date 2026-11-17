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
from gta6_impact.config import ROOT

CHARTS = ROOT / "charts"
THEMES = {"light": "dex-site", "dark": "dex-site-dark"}
LOGO = {"dex-site": "dex-logo-black.png", "dex-site-dark": "dex-logo-white.png"}
FOOT_RIGHT = "Built with <b>Dex</b> · trydex.ai"
SOURCE = 'Data source: Google Trends, US <span class="unit">· search interest, 0–100</span>'

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
<div class="card{variant}" style="width:{w}px;height:{h}px">
{aside}
  <div class="mast">
    <div class="brand"><img alt="Dex" src="../brand/assets/{logo}"></div>
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
    body: str,
    aside: str = "",
    source: str,
    w: int,
    h: int,
    data: dict | None,
    png: bool,
    variant: str = "",
) -> None:
    CHARTS.mkdir(exist_ok=True)
    if data is not None:
        (CHARTS / "data").mkdir(exist_ok=True)
        (CHARTS / "data" / f"{name}.json").write_text(json.dumps(data, indent=1, default=str))
    for theme_name, theme in THEMES.items():
        html = PAGE.format(
            theme=theme,
            variant=f" {variant}" if variant else "",
            title=escape(title),
            w=w,
            h=h,
            logo=LOGO[theme],
            aside=aside,
            body=body,
            source=source,
            foot_right=FOOT_RIGHT,
        )
        suffix = "" if theme_name == "light" else "-dark"
        path = CHARTS / f"{name}{suffix}.html"
        path.write_text(html)
        if png:
            capture(path, CHARTS / "png" / f"{name}-{theme_name}.png", w, h)


def _day(value: str) -> dt.date:
    return dt.date.fromisoformat(str(value)[:10])


def _span(first_week: dt.date, last_week: dt.date) -> str:
    """Google weeks run Sunday to Saturday; label a window by its first and last day."""
    last_day = last_week + dt.timedelta(days=6)
    if first_week.month == last_day.month:
        return f"{first_week.day}–{last_day.day} {last_day:%b %Y}"
    return f"{first_week.day} {first_week:%b} – {last_day.day} {last_day:%b %Y}"


def _bars(terms: list[dict], prior_year: str, current_year: str) -> str:
    """Per phrase, last year's interest above this year's (0-100 scale), the change at the end."""
    rows = [
        '<div class="yoy"><div></div><div class="key">'
        f'<span><i class="prior"></i>{prior_year}</span>'
        f'<span><i class="current"></i>{current_year}</span></div>'
    ]
    for r in terms:
        change = r["day_off_index_term_change"]
        bars = "".join(
            f'<b class="{cls}" style="width:{value:.1f}%">{value:.1f}</b>'
            for cls, value in (
                ("prior", r["day_off_index_term_prior"]),
                ("current", r["day_off_index_term_current"]),
            )
            if value is not None
        )
        rows.append(
            f'<div class="term">“{escape(r["day_off_index_term__term"])}”</div>'
            f'<div class="pair">{bars}</div>'
            f'<div class="change">{f"{change:+.0f}%" if change is not None else "n/a"}</div>'
        )
    rows.append("</div>")
    return "".join(rows)


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
    ordered = sorted(terms, key=lambda r: -(r["day_off_index_term_change"] or 0))
    body = f"""    <div class="hero">
      <div>
        <div class="big">{big}</div>
        <h1>US Google searches for skipping work (vs last year)</h1>
        <p class="fine">Average change in searches for “call in sick”, “sick day” and
        “day off work”, <span class="nw">{escape(current)}</span> vs
        <span class="nw">{escape(prior)}</span>.<br>GTA 6 launches 19 Nov.</p>
      </div>
      {_bars(ordered, prior[-4:], current[-4:])}
    </div>"""
    aside = """  <figure class="aside">
    <img alt="Lucia and Jason, the two leads of GTA 6" src="../assets/gta-6-lucia-and-the-guy.jpg">
  </figure>"""
    data = {
        "day_off_index": index,
        "breakdown": head[f"{window}breakdown"],
        "current_window": current,
        "prior_window": prior,
        "terms": ordered,
    }
    _write(
        "day-off-index",
        title="Day-Off Index",
        body=body,
        aside=aside,
        source=SOURCE,
        w=1200,
        h=630,
        data=data,
        png=png,
    )
    # The same card at 4:5 for mobile feeds (LinkedIn, X): same data, stacked layout.
    _write(
        "day-off-index-portrait",
        title="Day-Off Index",
        body=body,
        aside=aside,
        source=SOURCE,
        w=720,
        h=900,
        data=None,
        png=png,
        variant="portrait",
    )
    return data


PRODUCTIVITY_SOURCE = (
    'Data source: World Bank WDI, IMF WEO <span class="unit">· world, real terms</span>'
)
MEASURES = {
    "output_per_person": ("GDP per person", "s-study"),
    "output_per_worker": ("GDP per worker", "s-control"),
}


def _productivity_plot(rows: list[dict], w: int = 620, h: int = 380) -> str:
    """Both measures' change since GTA V, year by year, with the two launches marked."""
    years = sorted({r["world_productivity_key__data_year"] for r in rows})
    first, last = years[0], years[-1]
    top = max(r["world_productivity_change_since_gta_v"] or 0 for r in rows)
    ymax = 5 * (int(top) // 5 + 1)
    left, right, top_pad, bottom = 52, 196, 34, 40

    def x(year: int) -> float:
        return left + (year - first) / (last - first) * (w - left - right)

    def y(pct: float) -> float:
        return top_pad + (1 - pct / ymax) * (h - top_pad - bottom)

    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img">']
    for tick in range(0, ymax + 1, 5 if ymax <= 30 else 10):
        ty = y(tick)
        parts.append(
            f'<line class="grid" x1="{left}" x2="{w - right}" y1="{ty:.1f}" y2="{ty:.1f}"/>'
        )
        parts.append(
            f'<text class="tick" x="{left - 10}" y="{ty + 5:.1f}" text-anchor="end">{tick}%</text>'
        )
    for year, label in ((first, "GTA V"), (last, "GTA 6")):
        mx = f"{x(year):.1f}"
        parts.append(
            f'<line class="marker launch" x1="{mx}" x2="{mx}" '
            f'y1="{top_pad - 14}" y2="{h - bottom}"/>'
        )
        parts.append(
            f'<text class="marker-label launch" x="{mx}" y="{top_pad - 20}" '
            f'text-anchor="middle">{label}</text>'
        )
        parts.append(
            f'<text class="tick" x="{mx}" y="{h - bottom + 24}" text-anchor="middle">{year}</text>'
        )
    labels = []
    for measure, (name, cls) in MEASURES.items():
        points = [
            (r["world_productivity_key__data_year"], r["world_productivity_change_since_gta_v"])
            for r in sorted(rows, key=lambda r: r["world_productivity_key__data_year"])
            if r["world_productivity_key__measure"] == measure
            and r["world_productivity_change_since_gta_v"] is not None
        ]
        if not points:
            continue
        path = " ".join(
            f"{'M' if i == 0 else 'L'}{x(a):.1f},{y(b):.1f}" for i, (a, b) in enumerate(points)
        )
        parts.append(f'<path class="line {cls}" d="{path}"/>')
        end_year, end_pct = points[-1]
        parts.append(
            f'<circle class="end {cls}" cx="{x(end_year):.1f}" cy="{y(end_pct):.1f}" r="5"/>'
        )
        labels.append((y(end_pct), end_year, end_pct, name))
    # Direct labels at the right edge, nudged apart when the two ends sit close.
    labels.sort()
    for i in range(1, len(labels)):
        if labels[i][0] - labels[i - 1][0] < 50:
            labels[i] = (labels[i - 1][0] + 50, *labels[i][1:])
    lx = w - right + 14
    for ly, end_year, end_pct, name in labels:
        parts.append(
            f'<text class="direct" x="{lx}" y="{ly + 6:.1f}">{end_pct:+.0f}%'
            f'<tspan class="direct-name" x="{lx}" dy="18">{name}, {end_year}</tspan></text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def productivity_card(png: bool) -> dict:
    """Metric 2, GTA V to GTA 6: how much more productive the world got between the launches."""
    # Sorted, so the committed chart data does not churn on every refresh.
    rows = sorted(
        query(
            ["world_productivity_change_since_gta_v", "world_productivity"],
            ["world_productivity_key__measure", "world_productivity_key__data_year"],
        ),
        key=lambda r: (
            r["world_productivity_key__measure"],
            r["world_productivity_key__data_year"],
        ),
    )
    by = {
        (r["world_productivity_key__measure"], r["world_productivity_key__data_year"]): r
        for r in rows
    }
    last = max(r["world_productivity_key__data_year"] for r in rows)
    head = by[("output_per_person", last)]["world_productivity_change_since_gta_v"]
    big = f"{head:+.0f}<small>%</small>" if head is not None else "n/a"
    body = f"""    <div class="hero" style="flex-direction:row;align-items:center;gap:36px">
      <div style="flex:0 0 400px">
        <div class="big">{big}</div>
        <h1>How much more productive the world got between GTA&nbsp;V and GTA&nbsp;6</h1>
        <p class="fine">World real GDP per person, 2013 to {last}.</p>
      </div>
      <div class="plot" style="flex:1;height:380px;margin:0">{_productivity_plot(rows)}</div>
    </div>"""
    data = {"rows": rows}
    _write(
        "gta-v-to-gta-6",
        title="GTA V to GTA 6",
        body=body,
        source=PRODUCTIVITY_SOURCE,
        w=1200,
        h=630,
        data=data,
        png=png,
    )
    return data


def build(png: bool = True) -> dict:
    productivity = productivity_card(png)
    summary = index_card(png)
    summary["productivity"] = productivity["rows"]
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), default=str))
