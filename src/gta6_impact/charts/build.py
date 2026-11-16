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
from gta6_impact.charts.svg import Series, line_chart
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


def share_chart(png: bool) -> dict:
    rows = query(
        ["gta_share_of_day_off_talk", "day_off_mentions", "day_off_mentions_gta"],
        ["signal_day__days_from_release", "signal_day__study_year", "signal_day__source"],
        where="{{ Dimension('signal_day__source') }} = 'bluesky' "
        "and {{ Dimension('signal_day__days_from_release') }} >= -45",
    )
    series = {}
    for r in rows:
        if r["gta_share_of_day_off_talk"] is None:
            continue
        series.setdefault(r["signal_day__study_year"], []).append(
            (r["signal_day__days_from_release"], 100 * r["gta_share_of_day_off_talk"])
        )
    study = sorted(series.get(2026, []))
    control = sorted(series.get(2025, []))
    latest_day, latest = study[-1] if study else (None, 0)
    early = next((v for d, v in study if d == -14), None)
    svg = line_chart(
        [
            Series("2026", study, "s-study", "{:.1f}%"),
            Series("2025 control", control, "s-control", "{:.1f}%"),
        ],
        width=1096,
        height=300,
        x_min=-45,
        x_max=7,
        y_fmt="{:.0f}%",
        x_ticks=[-42, -35, -28, -21, -14, -7, 0, 7],
        x_label=lambda x: "Thu 19 Nov" if x == 0 else (f"{int(x)}d" if x < 0 else f"+{int(x)}d"),
        marker_label="GTA 6",
    )
    mult = f"{latest / early:.0f}×" if early else ""
    body = f"""    <h1>Of everyone posting about a day off, <em>{latest:.1f}%</em> now say GTA.</h1>
    <p class="lede">Share of Bluesky posts about a day off, PTO or calling in sick that also mention
    GTA, by day before release. {("Up " + mult + " in two weeks. ") if mult else ""}The same weeks
    of 2025 sit at zero.</p>
    <div class="plot">{svg}</div>"""
    data = {"rows": rows, "latest_days_from_release": latest_day, "latest_share_pct": latest}
    _write(
        "gta-share-of-day-off-talk",
        title="GTA share of day-off talk",
        meta=_today_meta(),
        body=body,
        source="Bluesky public search · UTC days · association, not causation",
        w=1200,
        h=630,
        data=data,
        png=png,
    )
    return data


def hype_chart(png: bool) -> dict:
    rows = query(
        ["gta_wiki_pageviews"],
        ["signal_day__days_from_release", "signal_day__study_year"],
        where="{{ Dimension('signal_day__days_from_release') }} >= -45",
    )
    by_year: dict[int, list] = {}
    for r in rows:
        if r["gta_wiki_pageviews"] is not None:
            by_year.setdefault(r["signal_day__study_year"], []).append(
                (r["signal_day__days_from_release"], r["gta_wiki_pageviews"] / 1000)
            )
    control = sorted(by_year.get(2025, []))
    peak = max(control, key=lambda p: p[1], default=None)
    notes = [(peak[0], peak[1], "Nov 2025: the delay to 2026")] if peak else []
    svg = line_chart(
        [
            Series("2026", sorted(by_year.get(2026, [])), "s-study", "{:.0f}k"),
            Series("2025", control, "s-control", "{:.0f}k"),
        ],
        width=1096,
        height=300,
        x_min=-45,
        x_max=7,
        y_fmt="{:.0f}k",
        x_ticks=[-42, -35, -28, -21, -14, -7, 0, 7],
        x_label=lambda x: "Thu 19 Nov" if x == 0 else (f"{int(x)}d" if x < 0 else f"+{int(x)}d"),
        marker_label="GTA 6",
        notes=notes,
    )
    body = f"""    <h1>The hype line: daily readers of the <em>GTA VI</em> Wikipedia article.</h1>
    <p class="lede">English Wikipedia user pageviews, by day before release, against the same
    weeks a year earlier.</p>
    <div class="plot">{svg}</div>"""
    _write(
        "gta-wikipedia-hype",
        title="GTA VI hype line",
        meta=_today_meta(),
        body=body,
        source="Wikimedia pageviews API · users, all access · UTC days",
        w=1200,
        h=630,
        data={"rows": rows},
        png=png,
    )
    return {"rows": rows}


def index_card(png: bool, share: dict) -> dict:
    rows = query(["day_off_index"], ["index_year__study_year"])
    idx = {r["index_year__study_year"]: r["day_off_index"] for r in rows}
    effect = query(["day_off_index_gta_effect"])[0]["day_off_index_gta_effect"]
    control = idx.get(2025)
    study = idx.get(2026)
    if study is None:
        big = f"{share['latest_share_pct']:.1f}<small>%</small>"
        h1 = "GTA 6 lands Thursday. We're counting who calls in sick."
        lede = (
            "The Day-Off Index compares Thursday 19 Nov with the Thursday before, across "
            "search, Bluesky and Reddit, net of the usual pre-Thanksgiving drift. "
            "Until then: the share of day-off posts that already mention GTA."
        )
        study_cell = "<b>pending Thu 19 Nov</b>"
        effect_cell = "<b>pending</b>"
    else:
        big = f"{study:.0f}"
        h1 = "The Day-Off Index for GTA 6 Thursday."
        lede = (
            "100 is a normal week. Thursday 19 Nov against Thursday 12 Nov, across search, "
            "Bluesky and Reddit."
        )
        study_cell = f'<b class="red">{study:.0f}</b>'
        effect_cell = f'<b class="red">{effect:.0f}</b>' if effect else "<b>n/a</b>"
    control_cell = f"<b>{control:.0f}</b>" if control else "<b>n/a</b>"
    body = f"""    <div class="hero">
      <div>
        <div class="big">{big}</div>
        <h1 style="margin-top:22px">{escape(h1)}</h1>
        <p class="lede">{escape(lede)}</p>
      </div>
      <div class="box">
        <div class="strip">Day-Off Index · 100 = normal</div>
        <div class="rows">
          <div class="row"><span>GTA week, 2026</span>{study_cell}</div>
          <div class="row"><span>Same week, 2025</span>{control_cell}</div>
          <div class="row"><span>Net of season</span>{effect_cell}</div>
        </div>
      </div>
    </div>"""
    data = {"index": idx, "gta_effect": effect, "share": share.get("latest_share_pct")}
    _write(
        "day-off-index",
        title="Day-Off Index",
        meta=_today_meta(),
        body=body,
        source="Google Trends · Bluesky · Reddit · public-signal proxy, not headcount",
        w=1200,
        h=630,
        data=data,
        png=png,
    )
    return data


def lifts_chart(png: bool) -> dict:
    rows = query(
        ["thursday_lift"],
        [
            "thursday_lift__source",
            "thursday_lift__signal",
            "thursday_lift__geo",
            "thursday_lift__study_year",
        ],
        where="{{ Dimension('thursday_lift__is_index_component') }}",
    )
    signals: dict[tuple, dict] = {}
    for r in rows:
        key = (r["thursday_lift__source"], r["thursday_lift__signal"], r["thursday_lift__geo"])
        signals.setdefault(key, {})[r["thursday_lift__study_year"]] = r["thursday_lift"]
    hi = 2.0
    for v in (x for d in signals.values() for x in d.values() if x):
        hi = max(hi, v * 1.1)

    def pct(v: float) -> float:
        return max(0.0, min(100.0, (v - 0) / hi * 100))

    bar_rows = []
    for (source, signal, geo), years in sorted(signals.items()):
        name = f"{source.replace('_', ' ')} · {signal.split(':', 1)[1]}" + (
            f" · {geo}" if source == "google_trends" else ""
        )
        s, c = years.get(2026), years.get(2025)
        study = (
            f'<div class="fill study" style="width:{pct(s):.1f}%"></div>'
            if s
            else '<div class="fill pending" style="width:' + f'{pct(1):.1f}%"></div>'
        )
        control = f'<div class="fill control" style="width:{pct(c):.1f}%"></div>' if c else ""
        val = f"{s:.2f}×" if s else "Thu →"
        bar_rows.append(
            f'<div class="bar-row" title="2026: {val} · 2025: {c or 0:.2f}×">'
            f'<div class="name">{escape(name)}</div>'
            f'<div class="track">{study}{control}<div class="par" style="left:{pct(1):.1f}%">'
            f'</div></div><div class="val">{val}</div></div>'
        )
    body = f"""    <h1>Thursday over Thursday, <em>signal by signal</em>.</h1>
    <p class="lede">Each bar is release Thursday over the Thursday before. The line is a normal
    week (1.0×). Grey is the same pair of Thursdays in 2025.</p>
    <div class="legend"><span><i class="study"></i>2026 (19 vs 12 Nov)</span>
    <span><i class="control"></i>2025 control (20 vs 13 Nov)</span></div>
    <div class="bars">{"".join(bar_rows)}</div>"""
    _write(
        "thursday-lifts",
        title="Thursday lifts",
        meta=_today_meta(),
        body=body,
        source="Index components only · UTC days · Trends values relative within request",
        w=1200,
        h=630,
        data={"rows": rows},
        png=png,
    )
    return {"rows": rows}


def build(png: bool = True) -> dict:
    share = share_chart(png)
    hype_chart(png)
    lifts_chart(png)
    return index_card(png, share)


if __name__ == "__main__":
    print(json.dumps(build(), default=str))
