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


GITHUB_SOURCE = (
    'Data source: GitHub Search API <span class="unit">· public activity, UTC days</span>'
)
GITHUB_ORDER = ("prs_opened", "prs_merged", "commits")


def _millions(v: float) -> str:
    return f"{v / 1e6:.2f}M" if v < 1e7 else f"{v / 1e6:.1f}M"


def _signed(v: float) -> str:
    """+3 or −3, with a real minus sign: a hyphen reads as a dash at display sizes."""
    return f"{v:+.0f}".replace("-", "\u2212")


def _short(day: dt.date) -> str:
    return f"{day.day} {day:%b}"


def _github_bars(rows: list[dict], prior: str, current: str) -> str:
    """Per activity, the baseline Thursday above release day, each pair on its own scale."""
    out = [
        '<div class="yoy"><div></div><div class="key">'
        f'<span><i class="prior"></i>{escape(prior)}</span>'
        f'<span><i class="current"></i>{escape(current)}</span></div>'
    ]
    for r in rows:
        change = r["github_activity_change"]
        pair = (
            ("prior", r["github_activity_baseline"]),
            ("current", r["github_activity_release_day"]),
        )
        top = max((v for _, v in pair if v is not None), default=0) or 1
        bars = "".join(
            f'<b class="{cls}" style="width:{100 * value / top:.1f}%">{_millions(value)}</b>'
            for cls, value in pair
            if value is not None
        )
        out.append(
            f'<div class="term">{escape(r["label"])}</div>'
            f'<div class="pair">{bars}</div>'
            f'<div class="change">{f"{_signed(change)}%" if change is not None else "n/a"}</div>'
        )
    out.append("</div>")
    return "".join(out)


def github_card(png: bool) -> dict | None:
    """Metric 4: GitHub on release day, with its breakdown on the same card. Drawn only once
    release day has been counted: a half-day count is not a count."""
    day = "github_release_day__"
    heads = query(
        ["github_release_day_change"],
        [f"{day}breakdown", f"{day}release_day", f"{day}baseline_start", f"{day}baseline_end"],
    )
    if not heads:
        return None
    head = heads[0]
    activities = query(
        ["github_activity_change", "github_activity_release_day", "github_activity_baseline"],
        ["github_activity__activity", "github_activity__activity_label"],
    )
    for r in activities:
        r["label"] = r["github_activity__activity_label"]
    rows = sorted(
        activities,
        key=lambda r: (
            GITHUB_ORDER.index(r["github_activity__activity"])
            if r["github_activity__activity"] in GITHUB_ORDER
            else 99
        ),
    )
    release = _day(head[f"{day}release_day__day"])
    first, last = _day(head[f"{day}baseline_start__day"]), _day(head[f"{day}baseline_end__day"])
    weeks = (last - first).days // 7 + 1
    if weeks == 1:
        # "the Thursday before (12 Nov)": one day, named plainly
        baseline = f"the {release:%A} before ({_short(first)})"
        legend = f"{first:%a %-d %b}"
    else:
        baseline = (
            f"the median of the {weeks} {release:%A}s before ({_short(first)}–{_short(last)})"
        )
        legend = f"Median {release:%A}"
    change = head["github_release_day_change"]
    data = {
        "github_release_day_change": change,
        "breakdown": head[f"{day}breakdown"],
        "release_day": str(release),
        "baseline_start": str(first),
        "baseline_end": str(last),
        "baseline_label": baseline,
        "baseline_legend": legend,
        "activities": rows,
    }
    if change is None:
        return data
    big = f"{_signed(change)}<small>%</small>"
    body = f"""    <div class="hero">
      <div>
        <div class="big">{big}</div>
        <h1>PRs opened on GitHub on GTA 6 release day</h1>
        <p class="fine">Pull requests opened on GitHub,
        <span class="nw">{release:%a %-d %b %Y}</span> vs
        <span class="nw">{escape(baseline)}</span>.<br>GTA 6 launched 19 Nov.</p>
      </div>
      {_github_bars(rows, legend, f"{release:%a %-d %b}")}
    </div>"""
    aside = """  <figure class="aside">
    <img alt="Lucia and Jason, the two leads of GTA 6" src="../assets/gta-6-lucia-and-the-guy.jpg">
  </figure>"""
    for name, w, h, variant in (
        ("github-release-day", 1200, 630, ""),
        ("github-release-day-portrait", 720, 900, "portrait"),
    ):
        _write(
            name,
            title="PRs opened on GTA 6 release day",
            body=body,
            aside=aside,
            source=GITHUB_SOURCE,
            w=w,
            h=h,
            data=data if not variant else None,
            png=png,
            variant=variant,
        )
    return data


PRODUCTIVITY_SOURCE = (
    "Data source: World Bank WDI, IMF WEO · world GDP per person, constant 2015 US$"
)
# Official game logos are third-party trademarks: kept local (brand/third-party/ is gitignored)
# and used only when present; without them the card falls back to a plain type lockup.
GAME_LOGOS = {
    "v": ("gta-v-logo.png", "GTA V"),
    "vi": ("gta-6-logo.svg", "GTA VI"),
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
    """Metric 2, GTA 5 to GTA 6, as a glow-up over the Dex footer: 2013 left, 2026 right."""
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
                title="GTA 5 to GTA 6",
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


WAIT_SOURCE = "Data source: World Bank WDI, IMF WEO · world real GDP, constant 2015 US$"
# Per size: card (w, h), art (w, h), scale, where the chart starts, CSS variant, the milestone
# card's width before scaling, and how cards pick a side of the line: "room" puts each where
# there is more space (the shallow landscape line), "alternate" takes turns in date order so
# no side crowds (the steep portrait line).
WAIT_SIZES = {
    "everything-we-made": ((1200, 630), (1200, 576), 1.0, 200, "", 112, "room"),
    "everything-we-made-portrait": (
        (1080, 1350),
        (1080, 1270),
        1.45,
        470,
        "portrait",
        96,
        "alternate",
    ),
}
# One picture per editorial milestone (brand/milestones/): file, and how it fits its tile.
# Logos sit whole on a white tile; photos fill theirs, cropped around the centre unless an
# alignment says otherwise (the RDR2 cover is tall: its top holds Arthur and the revolver).
MILESTONE_IMAGES = {
    "comet_landing": ("comet_landing.jpg", "xMidYMid slice"),
    "alphago": ("alphago.jpg", "xMidYMid slice"),
    "red_dead_redemption_2": ("red_dead_redemption_2.jpg", "xMidYMin slice"),
    "black_hole_image": ("black_hole_image.jpg", "xMidYMid slice"),
    "covid_vaccine": ("covid_vaccine.jpg", "xMidYMid slice"),
    "chatgpt": ("chatgpt.png", "xMidYMid meet"),
    "gta_vi_trailer_1": ("gta_vi_trailer_1.jpg", "xMidYMid slice"),
    "claude_code": ("claude_code.png", "xMidYMid meet"),
    "artemis_ii_flyby": ("artemis_ii_flyby.jpg", "xMidYMid slice"),
}
MONO = 0.6  # IBM Plex Mono advance width, in em: label wraps are computed, not measured


def _trillions(v: float) -> str:
    return f"${v / 1e12:,.0f}T"


def _wrap(text: str, width: int) -> list[str]:
    """Greedy wrap to `width` characters; two lines are rebalanced so neither is left a stub."""
    lines: list[str] = []
    for word in text.split():
        if lines and len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) == 2:
        words = text.split()
        splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
        lines = list(min(splits, key=lambda ab: max(len(ab[0]), len(ab[1]))))
    return lines


def _spread(targets: list[float], gap: float, lo: float, hi: float) -> list[float]:
    """Card centres as close to their dots as possible, at least `gap` apart, inside [lo, hi]:
    neighbours that would overlap merge into a block centred on their dots."""
    blocks: list[list[float]] = []  # [first index, count, sum of target - offset]
    for i, t in enumerate(targets):
        blocks.append([i, 1, t])
        while len(blocks) > 1:
            (_, n0, s0), (_, n1, s1) = blocks[-2], blocks[-1]
            if s0 / n0 + n0 * gap <= s1 / n1:
                break
            blocks[-2:] = [[blocks[-2][0], n0 + n1, s0 + s1 - n1 * n0 * gap]]
    pos = [b[2] / b[1] + j * gap for b in blocks for j in range(int(b[1]))]
    for i in range(len(pos)):
        pos[i] = max(pos[i], lo, pos[i - 1] + gap if i else lo)
    for i in reversed(range(len(pos))):
        pos[i] = min(pos[i], hi, pos[i + 1] - gap if i + 1 < len(pos) else hi)
    return pos


def _wait_line(
    points: list[tuple[dt.date, float]],
    marks: list[dict],
    card_w: float,
    placement: str,
    w: int,
    a: int,
    k: float,
    band_top: float,
) -> str:
    """Cumulative world output over the wait, each editorial milestone as a picture card tied to
    its dot: above the line where there is more room above it (early), below it otherwise."""
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
        anchor = "start" if year == first.year else "end" if year == last.year else "middle"
        axes.append(
            f'<text class="tick{" edge" if edge else ""}" x="{tx:.1f}" '
            f'y="{band_bot + 24 * k:.1f}" text-anchor="{anchor}" '
            f'font-size="{fs:.1f}">{year if edge else f"’{year % 100:02d}"}</text>'
        )
    parts = [f'<svg class="trend" viewBox="0 0 {w} {a}">']
    for era in ("v", "vi"):
        parts.append(f'<g class="axes {era}" clip-path="url(#c{era})">{"".join(axes)}</g>')
    xy = [(x(d), y(v)) for d, v in points]
    d = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(xy))
    parts.append(f'<path class="halo" d="{d}"/><path class="stroke" d="{d}"/>')

    def line_y(px: float) -> float:
        """The line's height at px (it rises left to right, so a span's extremes are its ends)."""
        for (ax, ay), (bx, by) in zip(xy, xy[1:], strict=False):
            if ax <= px <= bx:
                return ay + (by - ay) * (px - ax) / (bx - ax) if bx > ax else ay
        return xy[0][1] if px < xy[0][0] else xy[-1][1]

    # The card: picture on top, the label wrapped under it.
    cw, pad, lfs = card_w * k, 5 * k, 11 * k
    iw = cw - 2 * pad
    ih = iw * 0.56
    per_line = int(iw / (MONO * lfs))
    lh = lfs * 1.25
    gap, lead = cw + 6 * k, 20 * k

    dots = {m["id"]: (x(m["day"]), y(m["value"])) for m in marks}
    need = pad + ih + 6 * k + 3 * lh + 3 * k + lead  # a year, a two-line label, a leader
    sides: dict[str, list[dict]] = {"above": [], "below": []}
    for i, m in enumerate(sorted(marks, key=lambda m: m["day"])):
        _, py = dots[m["id"]]
        if placement == "alternate":
            # Take turns, unless the turn's side has no room for a card there.
            above = i % 2 == 0
            if not above and band_bot - py < need:
                above = True
            elif above and py - band_top < need:
                above = False
        else:
            above = py - band_top > band_bot - py
        sides["above" if above else "below"].append(m)

    leaders, glyphs, cards = [], [], []
    for side, ms in sides.items():
        ms.sort(key=lambda m: m["day"])
        centres = _spread(
            [dots[m["id"]][0] for m in ms], gap, left + cw / 2 + 4 * k, w - right - cw / 2
        )
        for m, cx in zip(ms, centres, strict=True):
            px, py = dots[m["id"]]
            x0, x1 = cx - cw / 2, cx + cw / 2
            lines = _wrap(m["label"], per_line)
            chh = pad + ih + 6 * k + (1 + len(lines)) * lh + 3 * k
            if side == "above":
                y1 = min(line_y(x0), line_y(x1), py) - lead
                y0 = y1 - chh
                ok = y0 >= band_top - 70 * k  # may rise into the headroom, not the headline
            else:
                y0 = max(line_y(x0), line_y(x1), py) + lead
                y1 = y0 + chh
                ok = y1 <= band_bot - 4 * k
            if not ok:
                print(json.dumps({"chart": "everything-we-made", "overflow": m["id"]}), flush=True)
            ex = min(max(px, x0 + 10 * k), x1 - 10 * k)
            leaders.append(
                f'<line class="leader" x1="{px:.1f}" y1="{py:.1f}" '
                f'x2="{ex:.1f}" y2="{y1 if side == "above" else y0:.1f}"/>'
            )
            if m["rockstar"]:
                r_, pts = 9 * k, []
                for j in range(10):
                    ang = -math.pi / 2 + j * math.pi / 5
                    rad = r_ if j % 2 == 0 else r_ * 0.45
                    pts.append(f"{px + rad * math.cos(ang):.1f},{py + rad * math.sin(ang):.1f}")
                glyphs.append(f'<polygon class="mark rockstar" points="{" ".join(pts)}"/>')
            else:
                glyphs.append(f'<circle class="mark" cx="{px:.1f}" cy="{py:.1f}" r="{6 * k:.1f}"/>')
            file, fit = MILESTONE_IMAGES.get(m["id"], (None, "xMidYMid slice"))
            kind = "logo" if fit.endswith("meet") else "photo"
            ix, iy = x0 + pad, y0 + pad
            tile = (
                f'<rect class="tile {kind}" x="{ix:.1f}" y="{iy:.1f}" '
                f'width="{iw:.1f}" height="{ih:.1f}"/>'
            )
            if file:
                inset = ih * 0.14 if kind == "logo" else 0
                tile += (
                    f'<image href="../brand/milestones/{file}" '
                    f'x="{ix + inset:.1f}" y="{iy + inset:.1f}" width="{iw - 2 * inset:.1f}" '
                    f'height="{ih - 2 * inset:.1f}" preserveAspectRatio="{fit}"/>'
                )
            ty = iy + ih + 6 * k + lfs
            label = f'<tspan class="year" x="{cx:.1f}" y="{ty:.1f}">{m["day"].year}</tspan>'
            label += "".join(
                f'<tspan x="{cx:.1f}" y="{ty + (i + 1) * lh:.1f}">{escape(t)}</tspan>'
                for i, t in enumerate(lines)
            )
            cls = "card rockstar" if m["rockstar"] else "card"
            cards.append(
                f'<g class="{cls}">'
                f'<rect class="shadow" x="{x0 + 4 * k:.1f}" y="{y0 + 4 * k:.1f}" '
                f'width="{cw:.1f}" height="{chh:.1f}" rx="{3 * k:.1f}"/>'
                f'<rect class="frame" x="{x0:.1f}" y="{y0:.1f}" width="{cw:.1f}" '
                f'height="{chh:.1f}" rx="{3 * k:.1f}"/>{tile}'
                f'<text text-anchor="middle" font-size="{lfs:.1f}">{label}</text></g>'
            )
    parts += leaders + glyphs + cards
    parts.append(
        f'<circle class="dot start" cx="{xy[0][0]:.1f}" cy="{xy[0][1]:.1f}" r="{7 * k:.1f}"/>'
        f'<circle class="dot end" cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="{10 * k:.1f}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def wait_card(png: bool) -> dict:
    """Metric 3, everything that happened before GTA 6: the running total of world output from
    GTA 5 to GTA 6, with the editorial milestones as picture cards on the line."""
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
                "milestone__is_editorial",
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
        month_end = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(
            days=1
        )
        if r["world_output_cumulative"] is not None and start < month_end < last_day:
            points.append((month_end, r["world_output_cumulative"]))
    points.append((last_day, headline))
    # The chart draws the editorial milestones: the layer's own filter picks them.
    editorial = query(
        ["wait_milestone_output"],
        ["milestone__milestone_id"],
        where="{{ Dimension('milestone__is_editorial') }} = true",
    )
    picked = {r["milestone__milestone_id"] for r in editorial}
    marks = [
        {
            "id": r["milestone__milestone_id"],
            "day": _day(r["milestone__event_date__day"]),
            "label": r["milestone__chart_label"],
            "value": r["wait_milestone_output"],
            "rockstar": r["milestone__category"] == "rockstar",
        }
        for r in milestones
        if r["milestone__milestone_id"] in picked and r["wait_milestone_output"] is not None
    ]
    for name, ((w, h), (aw, ah), k, band_top, variant, card_w, placement) in WAIT_SIZES.items():
        body = f"""    <div class="glowup wait" style="width:{aw}px;height:{ah}px;--k:{k}">
{_backdrop(aw, ah, k)}
{_wait_line(points, marks, card_w, placement, aw, ah, k, band_top)}
      <div class="era v">
        {_lockup("v")}
        <div class="num">
          <div class="when">{start:%d %b %Y}</div>
        </div>
      </div>
      <div class="era vi">
        {_lockup("vi")}
        <div class="num">
          <div class="when">{end:%d %b %Y}</div>
        </div>
      </div>
      <div class="titles">
        <div class="headline">Everything that happened before GTA 6</div>
        <div class="subhead"><b>{days:,}</b> days of waiting</div>
      </div>
    </div>"""
        for theme_name, theme in THEMES.items():
            html = GLOWUP_PAGE.format(
                title="Everything before GTA 6",
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
    summary["github"] = github_card(png)
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), default=str))
