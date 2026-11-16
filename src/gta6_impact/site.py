"""The GitHub Pages scoreboard: one static page, the same charts, a countdown, a table."""

from __future__ import annotations

import datetime as dt
import json
from html import escape

from gta6_impact.config import ROOT

SITE = ROOT / "site"
REPO = "https://github.com/exmergo/gta6-productivity-impact"
BASE = "https://exmergo.github.io/gta6-productivity-impact/"
CARDS = (("day-off-index", "The Day-Off Index and its breakdown"),)

PAGE = """<!doctype html>
<html lang="en" data-theme="dex-site">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GTA 6 vs. Productivity: the Day-Off Index</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{base}">
<link rel="icon" type="image/png" href="brand/assets/exmergo-mark-black.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="GTA 6 vs. Productivity">
<meta property="og:url" content="{base}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{base}charts/png/day-off-index-light.png">
<meta property="og:image:width" content="2400">
<meta property="og:image:height" content="1260">
<meta property="og:image:alt" content="{image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{base}charts/png/day-off-index-light.png">
<meta name="twitter:image:alt" content="{image_alt}">
<script type="application/ld+json">{jsonld}</script>
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
  dl dt {{ font-weight: 700; font-size: 18px; margin-top: 22px; }}
  dl dd {{ margin: 6px 0 0; font-size: 17px; line-height: 1.5; color: var(--dex-ink-muted); max-width: 860px; }}
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
<h2>Questions people ask</h2>
{faq}
<h2>Ask it yourself</h2>
<p class="lede">Every number here is a governed metric in a dbt semantic layer that Dex wrote and verified. Clone the repo and ask:</p>
<pre>git clone {repo}
cd gta6-productivity-impact
uv sync
uv run dbt parse
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
  }} else {{
    el.textContent = 'GTA 6 is out. We are counting.';
  }}
</script>
</body>
</html>
"""


def _pct(value: float | None) -> str:
    return f"{value:+.1f}%" if value is not None else "not yet available"


def _faq(summary: dict) -> list[tuple[str, str]]:
    """Question and answer pairs for the page and its FAQPage JSON-LD, numbers from the summary."""
    index = summary.get("day_off_index")
    if index is None:
        return []
    window = f"{summary['current_window']} against {summary['prior_window']}"
    parts = ", ".join(
        f"“{r['day_off_index_term__term']}” {_pct(r['day_off_index_term_change'])}"
        for r in sorted(summary["terms"], key=lambda r: -(r["day_off_index_term_change"] or 0))
    )
    return [
        (
            "Are Americans searching for sick days more before GTA 6?",
            f"{'Yes' if index > 0 else 'No'}. US Google searches for skipping work were "
            f"{'up' if index > 0 else 'down'} {abs(index):.0f}% on average, "
            f"{window}: {parts}. GTA 6 launches on Thursday 19 November 2026.",
        ),
        (
            "What is the Day-Off Index?",
            "The average year-over-year change in US Google searches for “call in sick”, "
            "“sick day” and “day off work”. Each phrase compares its average weekly Google "
            "Trends interest over two weeks with the same weeks a year earlier. It is always "
            "shown with its breakdown.",
        ),
        (
            "Did GTA 6 cause the rise?",
            "We can't say. The rise lines up with the run-up to GTA 6, but this is an "
            "association, not proof of cause. Search interest has other drivers too.",
        ),
        (
            "Is this how many people are taking the day off?",
            "No. It measures Google search interest (a 0–100 index), not a headcount. People "
            "who book time off in an HR system don't search for it.",
        ),
        (
            "How was it built?",
            "From public Google Trends data, with a dbt project and a MetricFlow semantic layer "
            "that Dex wrote, tested and verifies on every refresh. The repository is open "
            "source and every number can be reproduced from it.",
        ),
    ]


def _jsonld(summary: dict, faq: list[tuple[str, str]], description: str) -> str:
    dataset = {
        "@type": "Dataset",
        "name": "GTA 6 vs. Productivity: the Day-Off Index",
        "description": description,
        "url": BASE,
        "sameAs": REPO,
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "creator": {"@type": "Organization", "name": "Exmergo", "url": "https://trydex.ai"},
        "isAccessibleForFree": True,
        "spatialCoverage": "United States",
        "temporalCoverage": "2025-11-01/2026-11-14",
        "keywords": ["GTA 6", "productivity", "sick day", "call in sick", "Google Trends", "dbt"],
        "distribution": {
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": f"{BASE}charts/data/day-off-index.json",
        },
    }
    graph = [dataset]
    if faq:
        graph.append(
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a},
                    }
                    for q, a in faq
                ],
            }
        )
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return text.replace("</", "<\\/")


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
    faq = _faq(summary)
    headline_text = f"{index:+.0f}%" if index is not None else "not yet available"
    og_title = f"Day-Off Index: {headline_text}. Are Americans skipping work for GTA 6?"
    description = (
        f"US Google searches for “call in sick”, “sick day” and “day off work”, "
        f"{summary['current_window']} vs {summary['prior_window']}: {summary['breakdown']}. "
        "Open data, open method."
    )
    image_alt = (
        f"Day-Off Index {headline_text}: US Google searches for skipping work vs last year, "
        f"{summary['breakdown']}."
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
        base=BASE,
        description=escape(description),
        og_title=escape(og_title),
        image_alt=escape(image_alt),
        jsonld=_jsonld(summary, faq, description),
        faq="<dl>"
        + "".join(f"<dt>{escape(q)}</dt><dd>{escape(a)}</dd>" for q, a in faq)
        + "</dl>",
    )
    (SITE / "index.html").write_text(html)
    _crawlers(summary, faq)


def _crawlers(summary: dict, faq: list[tuple[str, str]]) -> None:
    """robots.txt, sitemap.xml and llms.txt: what search engines and answer engines read."""
    today = dt.datetime.now(dt.UTC).date().isoformat()
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{BASE}</loc><lastmod>{today}</lastmod></url>\n"
        f"  <url><loc>{BASE}llms.txt</loc><lastmod>{today}</lastmod></url>\n"
        "</urlset>\n"
    )
    qa = "\n\n".join(f"### {q}\n\n{a}" for q, a in faq)
    (SITE / "llms.txt").write_text(
        "# GTA 6 vs. Productivity\n\n"
        "> An open, reproducible study of whether Americans search for ways to skip work more "
        "in the run-up to GTA 6 (released 19 November 2026).\n\n"
        f"Updated {today}. Day-Off Index: {_pct(summary.get('day_off_index'))} "
        f"({summary['breakdown']}), {summary['current_window']} vs {summary['prior_window']}. "
        "Search interest, not a headcount; association, not causation.\n\n"
        f"## Questions\n\n{qa}\n\n"
        "## Links\n\n"
        f"- [Live scoreboard]({BASE})\n"
        f"- [Source code and README]({REPO})\n"
        f"- [Methodology]({REPO}/blob/main/docs/methodology.md)\n"
        f"- [Metric definitions]({REPO}/blob/main/docs/metrics.md)\n"
        f"- [Data sources]({REPO}/blob/main/docs/sources.md)\n"
        f"- [Chart data (JSON)]({BASE}charts/data/day-off-index.json)\n"
        "- [Dex](https://trydex.ai)\n"
    )
