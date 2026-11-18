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

GLOWUP_PAGE = """<!doctype html>
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
<div class="gcard{variant}" style="width:{w}px;height:{h}px">
{body}
  <div class="gfoot">
    <img class="dexlogo" alt="Dex" src="../brand/assets/{logo}">
    <span>{source}</span><span>{foot_right}</span>
  </div>
</div>
<script>
  if (document.documentElement.dataset.theme === 'dex-site-dark') {{
    document.querySelector('.dexlogo').src = '../brand/assets/dex-logo-white.png';
  }}
</script>
</body>
</html>
"""

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
    axes: list[str] = []
    step = 1000 if hi - lo > 1500 else 500
    for tick in range(math.ceil((lo + 1) / step) * step, hi + 1, step):
        ty = y(tick)
        axes.append(
            f'<line class="grid" x1="{left:.1f}" x2="{w - right:.1f}" '
            f'y1="{ty:.1f}" y2="{ty:.1f}"/>'
            f'<text class="tick" x="{left - 10 * k:.1f}" y="{ty + fs * 0.35:.1f}" '
            f'text-anchor="end" font-size="{fs:.1f}">${tick / 1000:g}k</text>'
        )
    axes.append(
        f'<line class="axis" x1="{left:.1f}" x2="{w - right:.1f}" '
        f'y1="{band_bot:.1f}" y2="{band_bot:.1f}"/>'
    )
    for year, _ in points:
        tx = x(year)
        edge = year in (first, last)
        axes.append(
            f'<line class="axis" x1="{tx:.1f}" x2="{tx:.1f}" '
            f'y1="{band_bot:.1f}" y2="{band_bot + 6 * k:.1f}"/>'
            f'<text class="tick{" edge" if edge else ""}" x="{tx:.1f}" '
            f'y="{band_bot + 24 * k:.1f}" text-anchor="middle" '
            f'font-size="{fs:.1f}">{year if edge else f"’{year % 100:02d}"}</text>'
        )
    # The axes switch ink with the background: drawn once per era, clipped to its half
    # (the clip paths live in the backdrop SVG of the same page).
    for era in ("v", "vi"):
        parts.append(f'<g class="axes {era}" clip-path="url(#c{era})">{"".join(axes)}</g>')
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


# Per size: card (w, h), the full-bleed art above the Dex footer strip (w, h), scale, and
# where the chart starts below the logo row. The strip's height matches .gfoot in charts.css.
GLOWUP_SIZES = {
    "gta-v-to-gta-6": ((1200, 630), (1200, 576), 1.0, 150, ""),
    "gta-v-to-gta-6-portrait": ((1080, 1350), (1080, 1270), 1.45, 400, "portrait"),
}


def productivity_card(png: bool) -> dict:
    """Metric 2, GTA V to GTA 6, as a glow-up over the Dex footer: 2013 left, 2026 right."""
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
        CHARTS.mkdir(exist_ok=True)
        (CHARTS / "data").mkdir(exist_ok=True)
        (CHARTS / "data" / "gta-v-to-gta-6.json").write_text(
            json.dumps({"rows": rows}, indent=1, default=str)
        )
        for theme_name, theme in THEMES.items():
            html = GLOWUP_PAGE.format(
                title="GTA V to GTA 6",
                theme=theme,
                variant=f" {variant}" if variant else "",
                w=w,
                h=h,
                logo=LOGO[theme],
                body=body,
                source=PRODUCTIVITY_SOURCE,
                foot_right=FOOT_RIGHT,
            )
            suffix = "" if theme_name == "light" else "-dark"
            path = CHARTS / f"{name}{suffix}.html"
            path.write_text(html)
            if png:
                capture(path, CHARTS / "png" / f"{name}-{theme_name}.png", w, h)
    return {"rows": rows}


WAIT_SOURCE = (
    "Data source: World Bank WDI, IMF WEO · world real GDP, constant 2015 US$ · "
    "milestones: our picks"
)
# Per size: card (w, h), art (w, h), scale, where the chart starts, CSS variant, and the hero
# milestones that get a label (the rest keep their dot; every one is in the site's table).
WAIT_SIZES = {
    "everything-we-made": ((1200, 630), (1200, 576), 1.0, 178, "", None),
    "everything-we-made-portrait": (
        (1080, 1350),
        (1080, 1270),
        1.45,
        430,
        "portrait",
        None,
    ),
}
# A few chips also carry what the world had made by then (the vaccine lands at about half
# the wait's output); more would clutter the line.
WAIT_PRICED = {"black_hole_image", "covid_vaccine", "chatgpt", "ship_catch"}
# The landscape card's labels, placed by hand (side, leader length, slide along the line) so
# the chips stack cleanly; a collision is still detected and logged. The rocket landing and
# booster catch keep their dots: the ship catch tells that story. A size without a layout
# places its labels greedily.
WAIT_LAYOUT = {
    "everything-we-made": {
        "comet_landing": ("above", 30, 0),
        "alphago": ("below", 16, 0),
        "red_dead_redemption_2": ("below", 30, 0),
        "black_hole_image": ("above", 60, 0),
        "covid_vaccine": ("below", 30, 0),
        "webb_first_images": ("above", 40, 0),
        "chatgpt": ("below", 40, 0),
        "crispr_therapy": ("above", 50, 0),
        "gta_vi_trailer_1": ("below", 28, -60),
        "renewables_beat_coal": ("above", 40, 0),
        "artemis_ii_flyby": ("below", 64, 0),
        "ship_catch": ("above", 40, 0),
    },
    "everything-we-made-portrait": {
        "comet_landing": ("above", 115, 0),
        "alphago": ("below", 28, 0),
        "red_dead_redemption_2": ("below", 28, 0),
        "black_hole_image": ("above", 40, 0),
        "covid_vaccine": ("below", 28, 0),
        "chatgpt": ("below", 30, 0),
        "gta_vi_trailer_1": ("below", 28, 0),
        "artemis_ii_flyby": ("above", 37, 0),
        "ship_catch": ("above", 40, 0),
    },
}
MONO = 0.6  # IBM Plex Mono advance width, in em: chip widths are computed, not measured


def _money(v: float) -> str:
    return f"${v / 1e15:.2f} quadrillion" if v >= 1e15 else f"${v / 1e12:,.0f}T"


def _trillions(v: float) -> str:
    return f"${v / 1e12:,.0f}T"


def _wait_line(
    points: list[tuple[dt.date, float]],
    marks: list[dict],
    labelled: set[str] | None,
    layout: dict | None,
    w: int,
    a: int,
    k: float,
    band_top: float,
) -> str:
    """Cumulative world output over the wait, milestones as dots on it, labels placed greedily
    in the open space: above-left of the rising line or below-right, never over it."""
    left, right, bottom = 78 * k, 34 * k, 34 * k
    band_bot = a - bottom
    first, last = points[0][0], points[-1][0]
    span = (last - first).days
    hi = math.ceil(max(v for _, v in points) / 250e12) * 250e12

    def x(day: dt.date) -> float:
        return left + (day - first).days / span * (w - left - right)

    def y(v: float) -> float:
        return band_bot - v / hi * (band_bot - band_top)

    fs = 13 * k
    axes: list[str] = []
    step = 250e12
    tick = 0.0
    while tick <= hi + 1:
        ty = y(tick)
        if tick:
            axes.append(
                f'<line class="grid" x1="{left:.1f}" x2="{w - right:.1f}" '
                f'y1="{ty:.1f}" y2="{ty:.1f}"/>'
            )
        axes.append(
            f'<text class="tick" x="{left - 10 * k:.1f}" y="{ty + fs * 0.35:.1f}" '
            f'text-anchor="end" font-size="{fs:.1f}">{_trillions(tick) if tick else "$0"}</text>'
        )
        tick += step
    axes.append(
        f'<line class="axis" x1="{left:.1f}" x2="{w - right:.1f}" '
        f'y1="{band_bot:.1f}" y2="{band_bot:.1f}"/>'
    )
    for year in range(first.year, last.year + 1):
        day = first if year == first.year else dt.date(year, 1, 1)
        edge = year in (first.year, last.year)
        if year == last.year:
            day = last
        tx = x(day)
        crowded = year == first.year + 1 and (day - first).days < 200
        axes.append(
            f'<line class="axis" x1="{tx:.1f}" x2="{tx:.1f}" '
            f'y1="{band_bot:.1f}" y2="{band_bot + 6 * k:.1f}"/>'
        )
        if crowded:
            continue
        axes.append(
            f'<text class="tick{" edge" if edge else ""}" x="{tx:.1f}" '
            f'y="{band_bot + 24 * k:.1f}" text-anchor="{"start" if year == first.year else "end" if year == last.year else "middle"}" '
            f'font-size="{fs:.1f}">{year if edge else f"’{year % 100:02d}"}</text>'
        )
    parts = [f'<svg class="trend" viewBox="0 0 {w} {a}">']
    for era in ("v", "vi"):
        parts.append(f'<g class="axes {era}" clip-path="url(#c{era})">{"".join(axes)}</g>')
    xy = [(x(d), y(v)) for d, v in points]
    d = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(xy))
    parts.append(f'<path class="halo" d="{d}"/><path class="stroke" d="{d}"/>')

    # Label placement: every rectangle a chip may not touch.
    def hits_line(r: tuple[float, float, float, float]) -> bool:
        x0, y0, x1, y1 = r
        for (ax, ay), (bx, by) in zip(xy, xy[1:], strict=False):
            if bx < x0 or ax > x1:
                continue
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):
                px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                if x0 <= px <= x1 and y0 <= py <= y1:
                    return True
        return False

    def overlaps(r, others, pad: float) -> bool:
        return any(
            r[0] < o[2] + pad and r[2] > o[0] - pad and r[1] < o[3] + pad and r[3] > o[1] - pad
            for o in others
        )

    dots = [(x(m["day"]), y(m["value"])) for m in marks]
    dot_boxes = [(px - 8 * k, py - 8 * k, px + 8 * k, py + 8 * k) for px, py in dots]
    placed: list[tuple[float, float, float, float]] = []
    segs: list[tuple[float, float, float, float]] = []

    def crosses(sg, r, pad: float) -> bool:
        """Does the leader segment sg pass through rectangle r (sampled; leaders are short)?"""
        ax, ay, bx, by = sg
        return any(
            r[0] - pad <= ax + (bx - ax) * t / 24 <= r[2] + pad
            and r[1] - pad <= ay + (by - ay) * t / 24 <= r[3] + pad
            for t in range(1, 24)
        )
    chips, leaders, glyphs = [], [], []
    cfs, pad_x, ch = 13 * k, 9 * k, 26 * k
    # Rockstar's nods go first (they only fit under the line), then the priced chips (the
    # story beats: black hole, vaccine, ChatGPT, ship catch), then the rest in date order, so
    # the few that cannot fit are never the headline ones.
    order = sorted(
        range(len(marks)),
        key=lambda i: (not marks[i]["rockstar"], marks[i]["id"] not in WAIT_PRICED, i),
    )
    for i in order:
        m, (px, py) = marks[i], dots[i]
        rockstar = m["rockstar"]
        if rockstar:
            r_, pts = 9 * k, []
            for j in range(10):
                ang = -math.pi / 2 + j * math.pi / 5
                rad = r_ if j % 2 == 0 else r_ * 0.45
                pts.append(f"{px + rad * math.cos(ang):.1f},{py + rad * math.sin(ang):.1f}")
            glyphs.append(f'<polygon class="mark rockstar" points="{" ".join(pts)}"/>')
        else:
            glyphs.append(f'<circle class="mark" cx="{px:.1f}" cy="{py:.1f}" r="{6 * k:.1f}"/>')
        if layout is not None:
            if m["id"] not in layout:
                continue
        elif labelled is not None and m["id"] not in labelled:
            continue
        text = m["label"] + (f" · {_trillions(m['value'])}" if m["id"] in WAIT_PRICED else "")
        cw = len(text) * MONO * cfs + 2 * pad_x
        # Rockstar nods sit under the line; achievements alternate, starting above.
        sides = ("below",) if rockstar else (("above", "below") if i % 2 == 0 else ("below", "above"))
        spot = None
        if layout is not None:
            side, lead, slide = layout[m["id"]]
            sides = (side,)
        for side in sides:
            leads = (lead,) if layout is not None else (28, 52, 76, 100, 124, 150, 178, 206, 236)
            for lead in leads:
                for slide in (slide,) if layout is not None else (0, 40, 90, 150, 220, -40, -90, -150):
                    lead_k, slide_k = lead * k, slide * k
                    if side == "above":
                        x0, y1 = px + 14 * k - cw - slide_k, py - lead_k
                        y0 = y1 - ch
                    else:
                        x0, y0 = px - 14 * k + slide_k, py + lead_k
                        y1 = y0 + ch
                    x0 = min(max(x0, left + 4 * k), w - right - cw)
                    box = (x0, y0, x0 + cw, y1)
                    seg = (px, py, min(max(px, x0 + 6 * k), x0 + cw - 6 * k), y1 if side == "above" else y0)
                    clash = (
                        y0 < band_top - 46 * k
                        or y1 > band_bot - 6 * k
                        or abs(seg[2] - seg[0]) > 60 * k  # leaders stay near vertical
                    )
                    if layout is not None:
                        if clash or hits_line(box) or overlaps(box, placed, 4 * k) or any(
                            crosses(seg, o, 1 * k) for o in placed
                        ):
                            print(json.dumps({"chart": "everything-we-made", "collision": m["id"]}), flush=True)
                        spot = (side, box, seg)
                        break
                    if clash:
                        continue
                    if (
                        hits_line(box)
                        or overlaps(box, placed, 6 * k)
                        or overlaps(box, dot_boxes, 2 * k)
                        or any(crosses(sg, box, 3 * k) for sg in segs)
                        or any(crosses(seg, o, 2 * k) for o in placed)
                    ):
                        continue
                    spot = (side, box, seg)
                    break
                if spot:
                    break
            if spot:
                break
        if spot is None:
            print(json.dumps({"chart": "everything-we-made", "unlabelled": m["id"]}), flush=True)
            continue
        side, (x0, y0, x1, y1), seg = spot
        placed.append((x0, y0, x1, y1))
        segs.append(seg)
        leaders.append(
            f'<line class="leader" x1="{seg[0]:.1f}" y1="{seg[1]:.1f}" x2="{seg[2]:.1f}" y2="{seg[3]:.1f}"/>'
        )
        cls = "chip rockstar" if rockstar else "chip"
        label = escape(m["label"])
        if m["id"] in WAIT_PRICED:
            label += f' <tspan class="price">· {escape(_trillions(m["value"]))}</tspan>'
        chips.append(
            f'<g class="{cls}"><rect x="{x0:.1f}" y="{y0:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
            f'rx="{3 * k:.1f}"/><text x="{x0 + pad_x:.1f}" y="{y0 + ch / 2 + cfs * 0.36:.1f}" '
            f'font-size="{cfs:.1f}">{label}</text></g>'
        )
    parts += leaders + glyphs + chips
    parts.append(
        f'<circle class="dot start" cx="{xy[0][0]:.1f}" cy="{xy[0][1]:.1f}" r="{7 * k:.1f}"/>'
        f'<circle class="dot end" cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="{10 * k:.1f}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def wait_card(png: bool) -> dict:
    """Metric 3, everything humanity made while waiting for GTA 6: the running total of world
    output from GTA V to GTA 6, with humanity's big moments on the line."""
    headline = query(["world_output_produced"])[0]["world_output_produced"]
    months = sorted(
        query(["world_output_cumulative"], ["metric_time__month"]),
        key=lambda r: r["metric_time__month"],
    )
    milestones = sorted(
        query(
            ["wait_milestone_output", "wait_milestone_share", "wait_milestone_days_to_gta_6"],
            [
                "milestone__milestone_id",
                "milestone__event_date",
                "milestone__chart_label",
                "milestone__title",
                "milestone__category",
                "milestone__tier",
                "milestone__date_precision",
                "milestone__source_url",
            ],
        ),
        key=lambda r: (str(r["milestone__event_date__day"]), r["milestone__milestone_id"]),
    )
    by_id = {r["milestone__milestone_id"]: r for r in milestones}
    gta_v, gta_6 = by_id["gta_v"], by_id["gta_6"]
    start = _day(gta_v["milestone__event_date__day"])
    end = _day(gta_6["milestone__event_date__day"])
    last_day = end - dt.timedelta(days=1)
    days = gta_v["wait_milestone_days_to_gta_6"]
    # The release-day ticker's rate: the last day of the wait, by the second.
    rate = query(
        ["world_output_per_second"],
        ["world_output_day__output_day"],
        where=f"{{{{ Dimension('world_output_day__output_day') }}}} = '{last_day}'",
    )[0]["world_output_per_second"]
    # Each month's running total is its last day's (a running total is never summed).
    points = [(start, gta_v["wait_milestone_output"])]
    for r in months:
        month = _day(r["metric_time__month"])
        month_end = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        if r["world_output_cumulative"] is not None and start < month_end < last_day:
            points.append((month_end, r["world_output_cumulative"]))
    points.append((last_day, headline))
    marks = [
        {
            "id": r["milestone__milestone_id"],
            "day": _day(r["milestone__event_date__day"]),
            "label": r["milestone__chart_label"],
            "value": r["wait_milestone_output"],
            "rockstar": r["milestone__category"] == "rockstar",
        }
        for r in milestones
        if r["milestone__tier"] == "hero" and r["wait_milestone_output"] is not None
    ]
    for name, ((w, h), (aw, ah), k, band_top, variant, labelled) in WAIT_SIZES.items():
        layout = WAIT_LAYOUT.get(name)
        body = f"""    <div class="glowup wait" style="width:{aw}px;height:{ah}px;--k:{k}">
{_backdrop(aw, ah, k)}
{_wait_line(points, marks, labelled, layout, aw, ah, k, band_top)}
      <div class="era v">
        {_lockup("v")}
        <div class="num">
          <div class="when">{start:%d %b %Y}</div>
          <div class="value">$0</div>
          <div class="what">made so far</div>
        </div>
      </div>
      <div class="era vi">
        {_lockup("vi")}
        <div class="num">
          <div class="when">{end:%d %b %Y}</div>
          <div class="value">{days:,}</div>
          <div class="what">days of waiting</div>
        </div>
      </div>
      <div class="badge">{_money(headline)}</div>
      <div class="sub">everything the world made while waiting for GTA 6</div>
    </div>"""
        for theme_name, theme in THEMES.items():
            html = GLOWUP_PAGE.format(
                title="Everything we made",
                theme=theme,
                variant=f" {variant}" if variant else "",
                w=w,
                h=h,
                logo=LOGO[theme],
                body=body,
                source=WAIT_SOURCE,
                foot_right=FOOT_RIGHT,
            )
            suffix = "" if theme_name == "light" else "-dark"
            path = CHARTS / f"{name}{suffix}.html"
            path.write_text(html)
            if png:
                capture(path, CHARTS / "png" / f"{name}-{theme_name}.png", w, h)
    data = {
        "world_output_produced": headline,
        "world_output_per_second": rate,
        "wait_start": str(start),
        "wait_last_day": str(last_day),
        "gta_6_release": str(end),
        "days": days,
        "months": months,
        "milestones": milestones,
    }
    (CHARTS / "data").mkdir(parents=True, exist_ok=True)
    (CHARTS / "data" / "everything-we-made.json").write_text(
        json.dumps(data, indent=1, default=str)
    )
    return data


def build(png: bool = True) -> dict:
    wait = wait_card(png)
    productivity = productivity_card(png)
    summary = index_card(png)
    summary["productivity"] = productivity["rows"]
    summary["wait"] = wait
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), default=str))
