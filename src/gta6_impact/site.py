"""The GitHub Pages scoreboard: one static page, the same charts, a countdown, a table."""

from __future__ import annotations

import datetime as dt
from html import escape

from gta6_impact.config import ROOT

SITE = ROOT / "site"
REPO = "https://github.com/exmergo/gta6-productivity-impact"
CARDS = (("day-off-index", "The Day-Off Index and its breakdown"),)

PAGE = """<!doctype html>
<html lang="en" data-theme="dex-site">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GTA 6 vs. Productivity</title>
<meta name="description" content="US Google searches for skipping work, against last year, in the run-up to GTA 6. Built with Dex.">
<meta property="og:title" content="GTA 6 vs. Productivity: the Day-Off Index">
<meta property="og:description" content="US Google searches for skipping work, against last year. Built with Dex.">
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
<h2>The breakdown, as the semantic layer returns it</h2>
<div class="wrap"><table>
<thead><tr><th>Search (US)</th><th class="num">{prior}</th><th class="num">{current}</th><th class="num">Change</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<p class="lede">Weekly Google Trends interest, one request per phrase spanning both years, so the
two years share one scale. Search interest, not a headcount.</p>
<h2>Ask it yourself</h2>
<p class="lede">Every number here is a governed metric in a dbt semantic layer that Dex wrote and verified. Clone the repo and ask:</p>
<pre>uv sync
uv run dex explore semantic query day_off_index --group-by day_off_index_window__breakdown
uv run dex explore semantic query day_off_index_term_change,day_off_index_term_prior,day_off_index_term_current --group-by day_off_index_term__term</pre>
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


def _pct(value: float | None) -> str:
    return f"{value:+.1f}%" if value is not None else "not yet available"


def build_site(summary: dict) -> None:
    SITE.mkdir(exist_ok=True)
    index = summary.get("day_off_index")
    if index is not None:
        headline = f"Day-Off Index: <em>{index:+.0f}%</em>."
    else:
        headline = "Day-Off Index: <em>not yet available</em>."
    lede = (
        f"US Google searches for skipping work, {summary['current_window']} against "
        f"{summary['prior_window']}: {summary['breakdown']}. The index is the average of the "
        "three. GTA 6 comes out on Thursday 19 November."
    )
    figures = "\n".join(
        f'<figure><img src="charts/png/{name}-light.png" data-dark="charts/png/{name}-dark.png" '
        f'alt="{escape(alt)}" loading="lazy"><figcaption>{escape(alt)} · '
        f'<a href="charts/data/{name}.json">data</a></figcaption></figure>'
        for name, alt in CARDS
    )
    rows = "".join(
        f"<tr><td>{escape(r['day_off_index_term__term'])}</td>"
        f"<td class='num'>{r['day_off_index_term_prior']:.1f}</td>"
        f"<td class='num'>{r['day_off_index_term_current']:.1f}</td>"
        f"<td class='num'>{_pct(r['day_off_index_term_change'])}</td></tr>"
        for r in sorted(summary["terms"], key=lambda r: r["day_off_index_term__term"])
    ) + (
        "<tr><td><b>Day-Off Index (average)</b></td><td></td><td></td>"
        f"<td class='num'><b>{_pct(index)}</b></td></tr>"
    )
    html = PAGE.format(
        updated=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        headline=headline,
        lede=escape(lede),
        countdown="GTA 6: Thursday 19 November",
        figures=figures,
        rows=rows,
        prior=escape(summary["prior_window"]),
        current=escape(summary["current_window"]),
        repo=REPO,
    )
    (SITE / "index.html").write_text(html)
