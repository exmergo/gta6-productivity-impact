"""The GitHub Pages scoreboard: one static page, the same charts, a countdown, a table."""

from __future__ import annotations

import datetime as dt
import json
from html import escape

from gta6_impact.config import ROOT

SITE = ROOT / "site"
REPO = "https://github.com/exmergo/gta6-productivity-impact"
CARDS = (
    ("day-off-index", "The Day-Off Index"),
    ("gta-share-of-day-off-talk", "GTA share of day-off talk"),
    ("thursday-lifts", "Thursday over Thursday, signal by signal"),
    ("gta-wikipedia-hype", "The hype line"),
)

PAGE = """<!doctype html>
<html lang="en" data-theme="dex-site">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GTA 6 vs. Productivity</title>
<meta name="description" content="How many people take Thursday off for GTA 6? A public-signal Day-Off Index, built with Dex.">
<meta property="og:title" content="GTA 6 vs. Productivity: the Day-Off Index">
<meta property="og:description" content="How many people take Thursday off for GTA 6? Built with Dex.">
<meta property="og:image" content="charts/png/day-off-index-light.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="brand/dex-site.css">
<script>
  try {{
    if (matchMedia('(prefers-color-scheme: dark)').matches)
      document.documentElement.dataset.theme = 'dex-site-dark';
  }} catch (e) {{}}
</script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--dex-paper); color: var(--dex-ink); font-family: var(--font-sans); }}
  main {{ max-width: 1240px; margin: 0 auto; padding: 40px 16px 64px; }}
  header {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }}
  header img {{ height: 30px; }}
  .meta {{ font: 14px var(--font-mono); color: var(--dex-line); text-transform: uppercase; letter-spacing: 1px; }}
  h1 {{ font-size: clamp(32px, 6vw, 60px); line-height: 1.04; letter-spacing: -1.5px; margin: 36px 0 12px; }}
  h1 em {{ font-style: normal; color: var(--dex-redline); }}
  .lede {{ font-size: clamp(18px, 2.4vw, 22px); line-height: 1.45; color: var(--dex-ink-muted); max-width: 860px; }}
  .countdown {{ font: 15px var(--font-mono); color: var(--dex-ink); border: 1px solid var(--dex-line); background: var(--dex-paper-raised); display: inline-block; padding: 10px 14px; margin-top: 8px; }}
  figure {{ margin: 36px 0 0; }}
  figure img {{ width: 100%; height: auto; display: block; border: 1px solid var(--dex-rule); }}
  figcaption {{ font: 13px var(--font-mono); color: var(--dex-ink-muted); margin-top: 8px; }}
  h2 {{ font-size: 28px; letter-spacing: -.5px; margin: 56px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
  th, td {{ text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--dex-rule); }}
  th {{ font: 13px var(--font-mono); color: var(--dex-ink-muted); text-transform: uppercase; font-weight: 400; }}
  td.num {{ font-family: var(--font-mono); text-align: right; }}
  .wrap {{ overflow-x: auto; }}
  code {{ font-family: var(--font-mono); font-size: .92em; background: var(--dex-paper-sunk); padding: 1px 5px; }}
  main {{ overflow-wrap: anywhere; }}
  img {{ max-width: 100%; }}
  pre {{ white-space: pre-wrap; font-family: var(--font-mono); font-size: 14px; background: var(--dex-paper-sunk); padding: 14px; overflow-x: auto; }}
  a {{ color: var(--dex-line); }}
  footer {{ margin-top: 64px; padding-top: 14px; border-top: 1px solid var(--dex-line-soft); font: 13px var(--font-mono); color: var(--dex-ink-muted); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
</style>
</head>
<body>
<main>
<header>
  <img id="logo" alt="Dex" src="brand/assets/dex-logo-black.png">
  <span class="meta">GTA 6 vs. productivity · updated {updated}</span>
</header>
<h1>{headline}</h1>
<p class="lede">{lede}</p>
<p class="countdown" id="countdown" data-release="2026-11-19T00:00:00Z">{countdown}</p>
{figures}
<h2>The numbers, as the semantic layer returns them</h2>
<div class="wrap"><table>
<thead><tr><th>Source</th><th>Signal</th><th>Geo</th><th>Year</th><th class="num">Lift</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<h2>Ask it yourself</h2>
<p class="lede">Every number here is a governed metric in a dbt semantic layer that Dex wrote and verified. Clone the repo and ask:</p>
<pre>uv sync
uv run dex explore semantic query gta_share_of_day_off_talk --group-by metric_time__day,signal_day__source
uv run dex explore semantic query day_off_index_2026,day_off_index_2025,day_off_index_gta_effect</pre>
<footer><span>Public-signal proxy, not headcount · UTC days · association, not causation</span>
<span><a href="{repo}">Source &amp; method</a> · Built with <a href="https://trydex.ai">Dex</a></span></footer>
</main>
<script>
  if (document.documentElement.dataset.theme === 'dex-site-dark') {{
    document.getElementById('logo').src = 'brand/assets/dex-logo-white.png';
    document.querySelectorAll('img[data-dark]').forEach(i => i.src = i.dataset.dark);
  }}
  const el = document.getElementById('countdown');
  const t = Date.parse(el.dataset.release) - Date.now();
  if (t > 0) {{
    const d = Math.floor(t / 864e5), h = Math.floor(t % 864e5 / 36e5);
    el.textContent = `GTA 6 in ${{d}}d ${{h}}h (UTC midnight, Thu 19 Nov)`;
  }}
</script>
</body>
</html>
"""


def _lift(value: float | None) -> str:
    return f"{value:.2f}×" if value else "pending"


def build_site(summary: dict) -> None:
    SITE.mkdir(exist_ok=True)
    idx = summary.get("index", {})
    study = idx.get(2026) or idx.get("2026")
    share = summary.get("share")
    if study:
        headline = f"Day-Off Index: <em>{study:.0f}</em>."
        lede = (
            "Thursday 19 November against the Thursday before, across Google Trends, "
            "Bluesky and Reddit. 100 is a normal week."
        )
    else:
        headline = f"<em>{share:.1f}%</em> of day-off posts already say GTA."
        lede = (
            "GTA 6 comes out on Thursday 19 November. We measure how many people take the "
            "day off, using public search and social signals, against the Thursday before "
            "and against the same week of 2025."
        )
    figures = "\n".join(
        f'<figure><img src="charts/png/{name}-light.png" data-dark="charts/png/{name}-dark.png" '
        f'alt="{escape(alt)}" loading="lazy"><figcaption>{escape(alt)} · '
        f'<a href="charts/data/{name}.json">data</a></figcaption></figure>'
        for name, alt in CARDS
    )
    lifts = json.loads((ROOT / "charts" / "data" / "thursday-lifts.json").read_text())["rows"]
    rows = "".join(
        f"<tr><td>{escape(r['thursday_lift__source'])}</td>"
        f"<td>{escape(r['thursday_lift__signal'])}</td><td>{escape(r['thursday_lift__geo'])}</td>"
        f"<td>{r['thursday_lift__study_year']}</td>"
        f"<td class='num'>{_lift(r['thursday_lift'])}</td></tr>"
        for r in sorted(
            lifts,
            key=lambda r: (
                r["thursday_lift__source"],
                r["thursday_lift__signal"],
                r["thursday_lift__geo"],
                r["thursday_lift__study_year"],
            ),
        )
    )
    html = PAGE.format(
        updated=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        headline=headline,
        lede=escape(lede),
        countdown="GTA 6: Thursday 19 November",
        figures=figures,
        rows=rows,
        repo=REPO,
    )
    (SITE / "index.html").write_text(html)
