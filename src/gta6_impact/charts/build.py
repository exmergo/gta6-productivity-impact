"""Draw the charts: semantic queries in, branded HTML cards and PNGs out.

charts/<name>.html is the card (light and dark through ?theme=), charts/png/<name>-<theme>.png
is the capture, and charts/data/<name>.json is exactly what the semantic layer returned.
"""

from __future__ import annotations

import datetime as dt
import json
import math
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
    "Data source: World Bank WDI, IMF WEO · world GDP per person, constant 2015 US$"
)
# Official game logos are third-party trademarks: kept local (brand/third-party/ is gitignored)
# and used only when present; without them the card falls back to a plain type lockup.
GAME_LOGOS = {
    "v": ("gta-v-logo.png", "GTA V"),
    "vi": ("gta-6-logo.svg", "GTA 6"),
}

# A skyline as (width, height) steps, read left to right; reused, mirrored, on both halves.
SKYLINE = [
    (26, 40),
    (18, 66),
    (30, 52),
    (14, 92),
    (24, 74),
    (34, 46),
    (16, 108),
    (28, 60),
    (20, 84),
    (36, 50),
    (18, 70),
    (26, 96),
    (22, 56),
    (30, 78),
    (16, 44),
]


def _palm(x: float, base: float, h: float, lean: float, cls: str) -> str:
    """An original, simple palm silhouette: a curved trunk and seven tapered leaves."""
    tx, ty = x + lean, base - h
    parts = [
        f'<path class="{cls} trunk" d="M{x:.1f},{base:.1f} Q{x + lean * 0.15:.1f},'
        f'{base - h * 0.6:.1f} {tx:.1f},{ty:.1f}"/>'
    ]
    s = h * 0.46
    leaves = (
        (-1.0, 0.55),
        (-0.95, 0.12),
        (-0.55, -0.32),
        (0.05, -0.45),
        (0.6, -0.3),
        (0.98, 0.1),
        (1.0, 0.55),
    )
    for dx, dy in leaves:
        ex, ey = tx + dx * s, ty + dy * s
        # The leaf arcs up from the crown and droops to its tip: two curves round a midrib.
        mx, my = tx + dx * s * 0.5, ty + (dy - 0.38) * s * 0.6
        half = s * 0.09
        parts.append(
            f'<path class="{cls} leaf" d="M{tx:.1f},{ty:.1f} '
            f"Q{mx:.1f},{my - half:.1f} {ex:.1f},{ey:.1f} "
            f'Q{mx:.1f},{my + half:.1f} {tx:.1f},{ty:.1f}Z"/>'
        )
    return f'<g class="{cls}">' + "".join(parts) + "</g>"


def _skyline(x0: float, x1: float, base: float, scale: float, cls: str, flip: bool) -> str:
    steps = SKYLINE[::-1] if flip else SKYLINE
    out, x, i = [], x0, 0
    while x < x1:
        bw, bh = steps[i % len(steps)]
        out.append(
            f'<rect x="{x:.1f}" y="{base - bh * scale:.1f}" '
            f'width="{bw * scale + 0.5:.1f}" height="{bh * scale:.1f}"/>'
        )
        x += bw * scale
        i += 1
    return f'<g class="{cls}">' + "".join(out) + "</g>"


def _backdrop(w: int, a: int, k: float) -> str:
    """The two eras behind everything: a faded 2013 postcard and a 2026 sunset, cut diagonally."""
    top, bot = w * 0.545, w * 0.455
    sun_r = 118 * k
    sun_cx, sun_cy = w * 0.80, a * 0.60
    stripes = "".join(
        f'<rect x="{sun_cx - sun_r:.1f}" y="{sun_cy + sun_r * f:.1f}" width="{2 * sun_r:.1f}" '
        f'height="{sun_r * g:.1f}" fill="black"/>'
        for f, g in ((0.18, 0.06), (0.36, 0.09), (0.56, 0.12), (0.78, 0.15))
    )
    base = a + 2
    return f"""    <svg class="backdrop" viewBox="0 0 {w} {a}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="gv" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" class="s-v-sky"/><stop offset="1" class="s-v-haze"/></linearGradient>
        <linearGradient id="gvi" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" class="s-vi-deep"/><stop offset=".45" class="s-vi-violet"/>
          <stop offset=".78" class="s-vi-pink"/>
          <stop offset="1" class="s-vi-gold"/></linearGradient>
        <linearGradient id="gsun" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" class="s-vi-gold"/><stop offset="1" class="s-vi-pink"/></linearGradient>
        <mask id="sunmask"><rect x="0" y="0" width="{w}" height="{a}" fill="white"/>{stripes}</mask>
        <clipPath id="cv"><polygon points="0,0 {top:.1f},0 {bot:.1f},{a} 0,{a}"/></clipPath>
        <clipPath id="cvi"><polygon points="{top:.1f},0 {w},0 {w},{a} {bot:.1f},{a}"/></clipPath>
      </defs>
      <g clip-path="url(#cv)">
        <rect width="{w}" height="{a}" fill="url(#gv)"/>
        <circle class="v-sun" cx="{w * 0.12:.1f}" cy="{a * 0.62:.1f}" r="{90 * k:.1f}"/>
        {_skyline(0, top, base, 1.15 * k, "v-city", False)}
        {_palm(w * 0.36, base + 4, 210 * k, 34 * k, "v-palm")}
        {_palm(w * 0.405, base + 4, 160 * k, -22 * k, "v-palm")}
        <rect class="v-grain" width="{w}" height="{a}"/>
      </g>
      <g clip-path="url(#cvi)">
        <rect width="{w}" height="{a}" fill="url(#gvi)"/>
        <circle cx="{sun_cx:.1f}" cy="{sun_cy:.1f}" r="{sun_r:.1f}"
          fill="url(#gsun)" mask="url(#sunmask)"/>
        {_skyline(bot, w, base, 1.3 * k, "vi-city", True)}
        {_palm(w * 0.585, base + 4, 230 * k, -36 * k, "vi-palm")}
        {_palm(w * 0.63, base + 4, 170 * k, 26 * k, "vi-palm")}
      </g>
      <line class="seam" x1="{top:.1f}" y1="-10" x2="{bot:.1f}" y2="{a + 10}"/>
    </svg>"""


def _glowup_line(points: list[tuple[int, float]], w: int, a: int, k: float, band_top: float) -> str:
    """World GDP per person 2013 to 2026 across both eras, on quiet dollar and year axes."""
    left, right, bottom = 70 * k, 30 * k, 34 * k
    band_bot = a - bottom
    first, last = points[0][0], points[-1][0]
    lo = math.floor(min(v for _, v in points) / 500) * 500
    hi = math.ceil(max(v for _, v in points) / 500) * 500

    def x(year: int) -> float:
        return left + (year - first) / (last - first) * (w - left - right)

    def y(v: float) -> float:
        return band_bot - (v - lo) / (hi - lo) * (band_bot - band_top)

    fs = 13 * k
    parts = [f'<svg class="trend" viewBox="0 0 {w} {a}">']
    step = 1000 if hi - lo > 1500 else 500
    for tick in range(math.ceil((lo + 1) / step) * step, hi + 1, step):
        ty = y(tick)
        parts.append(
            f'<line class="grid" x1="{left:.1f}" x2="{w - right:.1f}" '
            f'y1="{ty:.1f}" y2="{ty:.1f}"/>'
            f'<text class="tick" x="{left - 10 * k:.1f}" y="{ty + fs * 0.35:.1f}" '
            f'text-anchor="end" font-size="{fs:.1f}">${tick / 1000:g}k</text>'
        )
    parts.append(
        f'<line class="axis" x1="{left:.1f}" x2="{w - right:.1f}" '
        f'y1="{band_bot:.1f}" y2="{band_bot:.1f}"/>'
    )
    for year, _ in points:
        tx = x(year)
        edge = year in (first, last)
        parts.append(
            f'<line class="axis" x1="{tx:.1f}" x2="{tx:.1f}" '
            f'y1="{band_bot:.1f}" y2="{band_bot + 6 * k:.1f}"/>'
            f'<text class="tick{" edge" if edge else ""}" x="{tx:.1f}" '
            f'y="{band_bot + 24 * k:.1f}" text-anchor="middle" '
            f'font-size="{fs:.1f}">{year if edge else f"’{year % 100:02d}"}</text>'
        )
    d = " ".join(
        f"{'M' if i == 0 else 'L'}{x(yr):.1f},{y(v):.1f}" for i, (yr, v) in enumerate(points)
    )
    parts.append(f'<path class="halo" d="{d}"/><path class="stroke" d="{d}"/>')
    parts.append(
        f'<circle class="dot start" cx="{x(first):.1f}" cy="{y(points[0][1]):.1f}" '
        f'r="{7 * k:.1f}"/>'
        f'<circle class="dot end" cx="{x(last):.1f}" cy="{y(points[-1][1]):.1f}" '
        f'r="{10 * k:.1f}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _lockup(era: str) -> str:
    file, text = GAME_LOGOS[era]
    if (ROOT / "brand" / "third-party" / file).exists():
        return f'<img class="gamelogo" alt="{text} logo" src="../brand/third-party/{file}">'
    return f'<div class="gamelogo text">{text}</div>'


# Per size: card (w, h), the art panel inside the Dex frame (w, h), scale, and where the
# chart starts below the logo row. Panel sizes match the frame's padding in charts.css.
GLOWUP_SIZES = {
    "gta-v-to-gta-6": ((1200, 630), (1128, 478), 1.0, 150, ""),
    "gta-v-to-gta-6-portrait": ((1080, 1350), (1000, 1160), 1.45, 400, "portrait"),
}


def productivity_card(png: bool) -> dict:
    """Metric 2, GTA V to GTA 6, as a glow-up inside the Dex frame: 2013 left, 2026 right."""
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
    person = [
        r
        for r in rows
        if r["world_productivity_key__measure"] == "output_per_person"
        and r["world_productivity"] is not None
    ]
    start, end = person[0], person[-1]
    change = end["world_productivity_change_since_gta_v"]
    points = [(r["world_productivity_key__data_year"], r["world_productivity"]) for r in person]
    for name, ((w, h), (aw, ah), k, band_top, variant) in GLOWUP_SIZES.items():
        body = f"""    <div class="glowup" style="width:{aw}px;height:{ah}px;--k:{k}">
{_backdrop(aw, ah, k)}
{_glowup_line(points, aw, ah, k, band_top)}
      <div class="era v">
        {_lockup("v")}
        <div class="num">
          <div class="when">{start["world_productivity_key__data_year"]}</div>
          <div class="value">${start["world_productivity"]:,.0f}</div>
          <div class="what">world GDP per person</div>
        </div>
      </div>
      <div class="era vi">
        {_lockup("vi")}
        <div class="num">
          <div class="when">{end["world_productivity_key__data_year"]}</div>
          <div class="value">${end["world_productivity"]:,.0f}</div>
          <div class="what">world GDP per person</div>
        </div>
      </div>
      <div class="badge">{f"{change:+.0f}%" if change is not None else "n/a"}</div>
    </div>"""
        _write(
            name,
            title="GTA V to GTA 6",
            body=body,
            source=PRODUCTIVITY_SOURCE,
            w=w,
            h=h,
            data={"rows": rows},
            png=png,
            variant=f"frame {variant}".strip(),
        )
    return {"rows": rows}


def build(png: bool = True) -> dict:
    productivity = productivity_card(png)
    summary = index_card(png)
    summary["productivity"] = productivity["rows"]
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), default=str))
