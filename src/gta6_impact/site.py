"""The GitHub Pages scoreboard: one static page, the same charts, a countdown, a table."""

from __future__ import annotations

import datetime as dt
import json
from html import escape

from gta6_impact.config import RELEASE_DAY, ROOT

SITE = ROOT / "site"
REPO = "https://github.com/exmergo/gta6-productivity-impact"
BASE = "https://exmergo.github.io/gta6-productivity-impact/"
CARDS = (("day-off-index", "The Day-Off Index and its breakdown"),)
HERO = "everything-we-made"

PAGE = """<!doctype html>
<html lang="en" data-theme="dex-site">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{og_title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{base}">
<link rel="icon" type="image/png" href="brand/assets/exmergo-mark-black.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="GTA 6 vs. Productivity">
<meta property="og:url" content="{base}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{base}charts/png/{hero}-light.png">
<meta property="og:image:width" content="2400">
<meta property="og:image:height" content="1260">
<meta property="og:image:alt" content="{image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{base}charts/png/{hero}-light.png">
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
  h1 em, h2 em {{ font-style: normal; color: var(--dex-line); }}
  figure + .wrap {{ margin-top: 20px; }}
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
  .ticker {{ font: 700 clamp(26px, 5.4vw, 52px) var(--font-mono); letter-spacing: -1px; margin: 28px 0 0; font-variant-numeric: tabular-nums; }}
  .ticker small {{ display: block; font: 14px var(--font-mono); letter-spacing: 0; color: var(--dex-ink-muted); margin-top: 6px; }}
  .ticker .since {{ display: block; font-size: .5em; margin-top: 10px; color: var(--dex-line); }}
  .ticker .since:empty {{ display: none; }}
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
<p class="countdown" id="countdown" data-release="{release}">{countdown}</p>
{wait}
{productivity}
<h2>The combo breaker: people are already planning the day off</h2>
<p class="lede">Nobody publishes how many people booked that Thursday off. So we measured what
people <em>search</em> for when they're planning to skip work, against the same weeks last year.
{day_off_lede}</p>
{figures}
<div class="wrap"><table>
<thead><tr><th>Search (US)</th><th class="num">{prior}</th><th class="num">{current}</th><th class="num">Change</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<p class="lede">Weekly Google Trends interest, one request per phrase spanning both years, so the
two years share one scale. Search interest, not a headcount.</p>
{github}
<h2>Questions people ask</h2>
{faq}
<h2>Ask it yourself</h2>
<p class="lede">Every number here is a governed metric in a dbt semantic layer that Dex wrote and verified. Clone the repo and ask:</p>
<pre>git clone {repo}
cd gta6-productivity-impact
uv sync
uv run dbt parse
uv run dex explore semantic query world_output_produced
uv run dex explore semantic query wait_milestone_output --group-by milestone__title,milestone__event_date
uv run dex explore semantic query world_productivity_change_since_gta_v,world_productivity --group-by world_productivity_key__measure,world_productivity_key__data_year
uv run dex explore semantic query day_off_index --group-by day_off_index_window__breakdown
uv run dex explore semantic query day_off_index_term_change,day_off_index_term_prior,day_off_index_term_current --group-by day_off_index_term__term{github_ask}</pre>
<footer><span>Public-signal proxy, not headcount · UTC days · association, not causation</span>
<span><a href="{repo}">Source &amp; method</a> · Built with <a href="https://trydex.ai">Dex</a></span></footer>
</main>
<script>
  if (document.documentElement.dataset.theme === 'dex-site-dark') {{
    document.getElementById('logo').src = 'brand/assets/dex-logo-white.png';
    document.querySelectorAll('img[data-dark]').forEach(i => i.src = i.dataset.dark);
  }}
  // The ticker: world output since GTA 5, at the rate the semantic layer gives for the last
  // day of the wait. It stops at GTA 6's release; a second line counts on from there.
  const tk = document.getElementById('wait-ticker');
  if (tk) {{
    const total = tk.querySelector('.total'), since = tk.querySelector('.since');
    const anchor = Date.parse(tk.dataset.anchorTime), release = Date.parse(tk.dataset.release);
    const base = Number(tk.dataset.anchorTotal), rate = Number(tk.dataset.rate);
    const fmt = new Intl.NumberFormat('en-US', {{ maximumFractionDigits: 0 }});
    const draw = () => {{
      const now = Date.now();
      const made = base + rate * (Math.min(now, release) - anchor) / 1000;
      total.textContent = (now >= release ? 'Final: $' : '$') + fmt.format(made);
      since.textContent = now >= release
        ? 'Made since GTA 6: $' + fmt.format(rate * (now - release) / 1000) : '';
    }};
    draw();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) setInterval(draw, 1000);
    else {{
      let last = 0;
      const loop = t => {{ if (t - last > 100) {{ draw(); last = t; }} requestAnimationFrame(loop); }};
      requestAnimationFrame(loop);
    }}
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


def _quadrillions(v: float) -> str:
    return f"${v / 1e15:.2f} quadrillion"


def _trillions(v: float) -> str:
    return f"${v / 1e12:,.0f}T" if v else "$0"


def _when(r: dict) -> str:
    day = str(r["milestone__event_date__day"])[:10]
    return day[:7] if r.get("milestone__date_precision") == "month" else day


def _wait(summary: dict) -> dict | None:
    """Metric 3's facts, all from the semantic-query rows the chart drew."""
    wait = summary.get("wait")
    if not wait or wait.get("world_output_produced") is None:
        return None
    rows = wait["milestones"]
    by_id = {r["milestone__milestone_id"]: r for r in rows}
    total, rate = wait["world_output_produced"], wait["world_output_per_second"]
    chart = [r for r in rows if r["milestone__is_editorial"]]
    beats = [
        by_id[i]["milestone__chart_label"]
        for i in ("comet_landing", "black_hole_image", "ship_catch")
        if i in by_id
    ]
    return {
        "total": total,
        "rate": rate,
        "per_day": rate * 86400,
        "days": wait["days"],
        "start": dt.date.fromisoformat(wait["wait_start"]),
        "last_day": dt.date.fromisoformat(wait["wait_last_day"]),
        "release": dt.date.fromisoformat(wait["gta_6_release"]),
        "rows": rows,
        "chart": chart,
        "by_id": by_id,
        "beats": beats,
    }


def _wait_alt(w: dict) -> str:
    return (
        f"Everything that happened before GTA 6: {w['days']:,} days of waiting, from "
        f"{w['start']:%-d %b %Y} to {w['release']:%-d %b %Y}, from the comet landing and AlphaGo "
        "to ChatGPT, Claude Code and Artemis II, on the running total of world output."
    )


def _wait_section(summary: dict) -> str:
    """The release-day hook: the ticker, the chart, and every milestone with its source."""
    w = _wait(summary)
    if not w:
        return ""
    # The ticker counts up through the last day of the wait at that day's rate and lands on
    # the total at the release moment: anchored at the start of the last day.
    anchor_total = w["total"] - w["per_day"]
    release = f"{w['release']}T00:00:00Z"
    body = "".join(
        f"<tr><td class='num'>{escape(_when(r))}</td>"
        f"<td>{escape(r['milestone__title'])}</td>"
        f"<td class='num'>{_trillions(r['wait_milestone_output']) if r['wait_milestone_output'] is not None else 'n/a'}</td>"
        f'<td><a href="{escape(r["milestone__source_url"])}">source</a></td></tr>'
        for r in w["rows"]
    )
    alt = _wait_alt(w)
    return f"""<p class="ticker" id="wait-ticker" data-anchor-total="{anchor_total:.0f}" data-anchor-time="{w["last_day"]}T00:00:00Z" data-rate="{w["rate"]:.1f}" data-release="{release}"><span class="total">{_quadrillions(w["total"])}</span><span class="since"></span><small>made by the world since GTA 5, live at ${w["rate"] / 1e6:.1f} million a second, until GTA 6 (00:00 UTC, {w["release"]:%-d %b})</small></p>
<figure><img src="charts/png/everything-we-made-light.png" data-dark="charts/png/everything-we-made-dark.png" alt="{escape(alt)}"><figcaption>{escape(alt)} · <a href="charts/data/everything-we-made.json">data</a></figcaption></figure>
<div class="wrap"><table>
<thead><tr><th class="num">Date (UTC)</th><th>Meanwhile, humanity…</th><th class="num">Made since GTA 5</th><th>Source</th></tr></thead>
<tbody>{body}</tbody>
</table></div>
<p class="lede">World real GDP (World Bank WDI, constant 2015 US$), each year spread evenly over its
days; 2026 is the World Bank's 2025 figure grown by the IMF's 2026 world growth forecast. Each
milestone reads what the world had made by the day before it, with one public source each.</p>"""


PRODUCTIVITY_MEASURES = (
    ("output_per_person", "GDP per person (constant 2015 US$)"),
    ("output_per_worker", "GDP per worker (constant 2021 PPP $)"),
)


def _productivity_rows(summary: dict) -> list[dict]:
    """Per measure: the GTA 5 year, the latest year with a value, and the change between."""
    rows = summary.get("productivity") or []
    out = []
    for measure, label in PRODUCTIVITY_MEASURES:
        series = sorted(
            (r for r in rows if r["world_productivity_key__measure"] == measure),
            key=lambda r: r["world_productivity_key__data_year"],
        )
        valued = [r for r in series if r["world_productivity"] is not None]
        if not valued:
            continue
        first, last = valued[0], valued[-1]
        out.append(
            {
                "label": label,
                "first_year": first["world_productivity_key__data_year"],
                "first": first["world_productivity"],
                "last_year": last["world_productivity_key__data_year"],
                "last": last["world_productivity"],
                "change": last["world_productivity_change_since_gta_v"],
            }
        )
    return out


def _down_years(summary: dict, measure: str = "output_per_person") -> list[int]:
    """Years in which the measure fell against the year before: the breaks in the streak."""
    series = sorted(
        (
            r
            for r in summary.get("productivity") or []
            if r["world_productivity_key__measure"] == measure
            and r["world_productivity"] is not None
        ),
        key=lambda r: r["world_productivity_key__data_year"],
    )
    return [
        b["world_productivity_key__data_year"]
        for a, b in zip(series, series[1:], strict=False)
        if b["world_productivity"] < a["world_productivity"]
    ]


def _streak_line(summary: dict) -> str:
    down = _down_years(summary)
    if not down:
        return "It went up every single year."
    if len(down) == 1:
        return f"It went up every year except {down[0]}."
    return "It fell only in " + ", ".join(str(y) for y in down) + "."


def _productivity_section(summary: dict) -> str:
    """The hero: the glow-up chart and its table, under the streak headline."""
    rows = _productivity_rows(summary)
    if not rows:
        return ""
    body = "".join(
        f"<tr><td>{escape(r['label'])}</td>"
        f"<td class='num'>${r['first']:,.0f}</td>"
        f"<td class='num'>${r['last']:,.0f} ({r['last_year']})</td>"
        f"<td class='num'>{_pct(r['change'])}</td></tr>"
        for r in rows
    )
    head = rows[0]
    alt = (
        f"GTA 5 to GTA 6: world GDP per person ${head['first']:,.0f} in {head['first_year']} "
        f"and ${head['last']:,.0f} in {head['last_year']}, {_pct(head['change'])}"
    )
    bridge = (
        "And it wasn't just more people making more: each person made more, almost every year."
        if _wait(summary)
        else ""
    )
    return f"""<h2>The streak: the world got {head["change"]:.0f}% more productive while it waited</h2>
<p class="lede">{escape(bridge)} {escape(_streak_line(summary))}</p>
<figure><img loading="lazy" src="charts/png/gta-v-to-gta-6-light.png" data-dark="charts/png/gta-v-to-gta-6-dark.png" alt="{alt}"><figcaption>{alt} · <a href="charts/data/gta-v-to-gta-6.json">data</a></figcaption></figure>
<div class="wrap"><table>
<thead><tr><th>World, real terms</th><th class="num">2013 (GTA 5)</th><th class="num">Latest</th><th class="num">Change</th></tr></thead>
<tbody>{body}</tbody>
</table></div>
<p class="lede">World Bank WDI. 2026 is the World Bank's 2025 figure grown by the IMF's 2026 world
growth forecast. GTA 6 comes out on Thursday 19 November 2026. Is it the combo breaker?</p>"""


GITHUB_BRIDGE = """<p class="lede">Whether the streak actually breaks shows up after release: GitHub pull requests,
Wikipedia edits and the recovery curve are next in <a href="{repo}#the-series">the series</a>.</p>"""
GITHUB_ASK = (
    "\nuv run dex explore semantic query github_release_day_change "
    "--group-by github_release_day__breakdown"
    "\nuv run dex explore semantic query github_activity_change,github_activity_baseline,"
    "github_activity_release_day --group-by github_activity__activity"
)


def _github(summary: dict) -> dict | None:
    """Metric 4, once release day has been counted; None before that."""
    g = summary.get("github")
    if not g or g.get("github_release_day_change") is None:
        return None
    return g


def _count(v: float) -> str:
    return f"{v / 1e6:.2f} million" if v < 1e7 else f"{v / 1e6:.1f} million"


def _github_parts(g: dict) -> str:
    return "; ".join(
        f"{r['label']} {_pct(r['github_activity_change'])}"
        f" ({_count(r['github_activity_release_day'])} against "
        f"{_count(r['github_activity_baseline'])})"
        for r in g["activities"]
    )


def _thursday_run(g: dict) -> str:
    """How many same weekdays before release day in a row rose on the week before, from the
    semantic layer's rows; empty when there is no run to report."""
    rows = [r for r in g.get("thursdays", []) if r["github_activity_change_wow"] is not None]
    if len(rows) < 2:
        return ""
    *before, release = rows
    run = 0
    for r in reversed(before):
        if r["github_activity_change_wow"] <= 0:
            break
        run += 1
    if not run or release["github_activity_change_wow"] >= 0:
        return ""
    first = dt.date.fromisoformat(before[-run]["metric_time__day"][:10])
    return (
        f"Every {dt.date.fromisoformat(release['metric_time__day'][:10]):%A} from "
        f"{first:%-d %b} to the week before had more PRs opened than the one before it "
        f"({run} in a row). Release day had fewer."
    )


def _significance_text(g: dict) -> str:
    """One plain sentence for the curious: release day against its prediction, and the test."""
    s = g.get("significance")
    if not s or s["pct_vs_expected"] >= 0:
        return ""
    p = s["p_one_sided"]
    observed = next(
        r["github_activity_release_day"]
        for r in g["activities"]
        if r["github_activity__activity"] == s["activity"]
    )
    verdict = "statistically significant" if p < 0.05 else "not statistically significant"
    return (
        f"Taking GitHub's growth and its weekly rhythm into account, release day should have "
        f"seen about {_count(s['expected_count'])} PRs opened. It saw "
        f"{_count(observed)}: "
        f"{abs(s['pct_vs_expected']):.1f}% fewer. That shortfall is {verdict} "
        f"(one-sided t-test, p = {p:.2f}): on an ordinary day, a gap this big would turn up "
        f"about {round(100 * p)} times in 100."
    )


def _significance_line(g: dict) -> str:
    text = _significance_text(g)
    return f'\n<p class="lede">{escape(text)}</p>' if text else ""


def _github_section(summary: dict) -> str:
    g = _github(summary)
    if not g:
        return GITHUB_BRIDGE.format(repo=REPO)
    change = g["github_release_day_change"]
    release = dt.date.fromisoformat(g["release_day"])
    went = "went quiet" if change < 0 else "didn't go quiet"
    rows = "".join(
        f"<tr><td>{escape(r['label'])}</td>"
        f"<td class='num'>{r['github_activity_baseline']:,.0f}</td>"
        f"<td class='num'>{r['github_activity_release_day']:,.0f}</td>"
        f"<td class='num'>{_pct(r['github_activity_change'])}</td></tr>"
        for r in g["activities"]
    )
    head = next(r for r in g["activities"] if r["github_activity__activity"] == "prs_opened")
    others = ", ".join(
        f"{r['label']} {_pct(r['github_activity_change'])}"
        for r in g["activities"]
        if r is not head
    )
    name = "github-release-day"
    alt = (
        f"PRs opened on GitHub on GTA 6 release day: {_pct(change)} against "
        f"{g['baseline_label']}. {_github_parts(g)}."
    )
    return f"""<h2>The verdict: GitHub {went} on release day</h2>
<p class="lede">GitHub's own search counts, {release:%A} {release:%-d %B %Y} (UTC) against
{escape(g["baseline_label"])}.
Pull requests opened: <b>{_pct(change)}</b> ({_count(head["github_activity_release_day"])}
against {_count(head["github_activity_baseline"])}). {escape(_thursday_run(g))} Beside it:
{escape(others)}.</p>{_significance_line(g)}
<figure><img src="charts/png/{name}-light.png" data-dark="charts/png/{name}-dark.png"
alt="{escape(alt)}" loading="lazy"><figcaption>GitHub on GTA 6 release day ·
<a href="charts/data/{name}.json">data</a></figcaption></figure>
<div class="wrap"><table>
<thead><tr><th>GitHub</th><th class="num">{escape(g["baseline_legend"])}</th><th class="num">{release:%-d %b}</th><th class="num">Change</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<p class="lede">Wikipedia edits and the recovery curve are next in
<a href="{REPO}#the-series">the series</a>.</p>"""


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
    faq = [
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
    g = _github(summary)
    if g:
        change = g["github_release_day_change"]
        release = dt.date.fromisoformat(g["release_day"])
        faq.insert(
            0,
            (
                "Did GitHub go quiet on GTA 6 release day?",
                f"{'Yes' if change < 0 else 'No'}. On {release:%A} {release:%-d %B %Y} (UTC), "
                f"pull requests opened on GitHub were {_pct(change)} against "
                f"{g['baseline_label']}: {_github_parts(g)}. GitHub Search "
                "API counts; a change on release day is association, not proof of cause.",
            ),
        )
        if _significance_text(g):
            faq.insert(1, ("Is the drop statistically significant?", _significance_text(g)))
    productivity = _productivity_rows(summary)
    w = _wait(summary)
    if productivity:
        parts = "; ".join(
            f"{r['label']} {_pct(r['change'])} ({r['first_year']} to {r['last_year']})"
            for r in productivity
        )
        faq.insert(
            0,
            (
                "How much more productive did the world get between GTA 5 and GTA 6?",
                f"World real output grew by about a quarter between GTA 5 (2013) and GTA 6 "
                f"(2026): {parts}. {_streak_line(summary)} World Bank data; 2026 is the World "
                "Bank's 2025 figure grown by the IMF's 2026 world growth forecast.",
            ),
        )
    if w:
        by = w["by_id"]
        examples = "; ".join(
            f"{by[i]['milestone__title']}: {_trillions(by[i]['wait_milestone_output'])}"
            for i in ("black_hole_image", "covid_vaccine", "ship_catch")
            if i in by and by[i]["wait_milestone_output"] is not None
        )
        faq[0:0] = [
            (
                "How much did the world produce between GTA 5 and GTA 6?",
                f"About {_quadrillions(w['total'])} of goods and services in real terms "
                f"(constant 2015 US$), over the {w['days']:,} days from GTA 5's release "
                f"({w['start']:%-d %B %Y}) to the day before GTA 6 ({w['last_day']:%-d %B %Y}). "
                f"In 2026 the world makes about ${w['rate'] / 1e6:.1f} million a second, or "
                f"${w['per_day'] / 1e9:,.0f} billion a day. World Bank world GDP; 2026 is the "
                "World Bank's 2025 figure grown by the IMF's 2026 world growth forecast.",
            ),
            (
                "Is that in today's dollars?",
                "No. It's real output at 2015 prices (constant 2015 US$), so years compare "
                "fairly. In today's prices the figure would be larger. The per-second rate is a "
                "yearly average spread evenly; nobody measures GDP by the second.",
            ),
            (
                "Why these milestones?",
                "They're moments most people remember, not a ranking, each dated to "
                "a UTC day and backed by one public source, listed on the scoreboard. Each one "
                "reads what the world had made since GTA 5 by the day before it. "
                f"For example, {examples}.",
            ),
        ]
    return faq


def _jsonld(summary: dict, faq: list[tuple[str, str]], description: str) -> str:
    dataset = {
        "@type": "Dataset",
        "name": "GTA 6 vs. Productivity",
        "description": description,
        "url": BASE,
        "sameAs": REPO,
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
        "creator": {"@type": "Organization", "name": "Exmergo", "url": "https://trydex.ai"},
        "isAccessibleForFree": True,
        "spatialCoverage": ["World", "United States"],
        "temporalCoverage": "2013/2026",
        "keywords": [
            "GTA 6",
            "GTA 5",
            "GTA V",
            "productivity",
            "GDP per person",
            "world GDP",
            "sick day",
            "call in sick",
            "Google Trends",
            "GitHub",
            "pull requests",
            "dbt",
        ],
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": "application/json",
                "contentUrl": f"{BASE}charts/data/{name}.json",
            }
            for name in (HERO, "gta-v-to-gta-6", "day-off-index")
            + (("github-release-day",) if _github(summary) else ())
        ],
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
    streak = _productivity_rows(summary)
    head = streak[0] if streak else None
    w = _wait(summary)
    if w:
        headline = (
            f"Between GTA 5 and GTA 6, humanity made <em>{escape(_quadrillions(w['total']))}</em> "
            "of stuff."
        )
        beats = ". ".join(w["beats"])
        lede = (
            f"{w['days']:,} days of world output, from {w['start']:%-d %B %Y} to the night "
            f"before GTA 6. {beats}. Now we play GTA."
        )
    elif head and head["change"] is not None:
        headline = (
            f"Between GTA 5 and GTA 6, the world got <em>{head['change']:.0f}%</em> more "
            "productive."
        )
        lede = (
            f"World GDP per person, {head['first_year']} to {head['last_year']}: "
            f"${head['first']:,.0f} to ${head['last']:,.0f}. {_streak_line(summary)} GTA 6 "
            "comes out on Thursday 19 November 2026. Is it the combo breaker?"
        )
    else:
        headline = "GTA 6 vs. Productivity"
        lede = "GTA 6 comes out on Thursday 19 November 2026. Is it the combo breaker?"
    day_off_lede = (
        f"US Google searches for skipping work, {summary['current_window']} against "
        f"{summary['prior_window']}: {summary['breakdown']}. The Day-Off Index, the average of "
        f"the three: {_pct(index)}."
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
    if w:
        og_title = f"Everything humanity made while waiting for GTA 6: {_quadrillions(w['total'])}"
        image_alt = _wait_alt(w)
        streak_text = (
            f"Between GTA 5 and GTA 6 the world made {_quadrillions(w['total'])} of real "
            f"output in {w['days']:,} days. "
            + (
                f"World GDP per person rose {_pct(head['change'])}. {_streak_line(summary)} "
                if head and head["change"] is not None
                else ""
            )
        )
    elif head and head["change"] is not None:
        og_title = (
            f"GTA 5 to GTA 6: the world got {head['change']:.0f}% more productive. "
            "Is GTA 6 the combo breaker?"
        )
        image_alt = (
            f"GTA 5 to GTA 6: world GDP per person ${head['first']:,.0f} in "
            f"{head['first_year']} and ${head['last']:,.0f} in {head['last_year']}, "
            f"{_pct(head['change'])}."
        )
        streak_text = (
            f"World GDP per person rose {_pct(head['change'])} between GTA 5 "
            f"({head['first_year']}) and GTA 6 ({head['last_year']}). {_streak_line(summary)} "
        )
    else:
        og_title = "GTA 6 vs. Productivity"
        image_alt = "GTA 5 to GTA 6: world GDP per person"
        streak_text = ""
    description = (
        f"{streak_text}The combo breaker? US Google searches for skipping work "
        f"{summary['current_window']} vs {summary['prior_window']}: Day-Off Index {_pct(index)} "
        f"({summary['breakdown']}). "
        + (
            f"The verdict: pull requests opened on GitHub on GTA 6 release day "
            f"{_pct(g['github_release_day_change'])} against {g['baseline_label']}. "
            if (g := _github(summary))
            else ""
        )
        + "An open, reproducible study built with Dex."
    )
    html = PAGE.format(
        updated=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        headline=headline,
        lede=escape(lede),
        countdown="GTA 6: Thursday 19 November",
        release=f"{RELEASE_DAY}T00:00:00Z",
        wait=_wait_section(summary),
        figures=figures,
        day_off_lede=escape(day_off_lede),
        hero=HERO,
        productivity=_productivity_section(summary),
        github=_github_section(summary),
        github_ask=GITHUB_ASK if _github(summary) else "",
        rows=rows,
        prior=escape(summary["prior_window"]),
        current=escape(summary["current_window"]),
        repo=REPO,
        base=BASE,
        description=escape(description),
        og_title=escape(og_title),
        image_alt=escape(image_alt),
        jsonld=_jsonld(summary, faq, description),
        faq="<dl>" + "".join(f"<dt>{escape(q)}</dt><dd>{escape(a)}</dd>" for q, a in faq) + "</dl>",
    )
    (SITE / "index.html").write_text(html)
    _crawlers(summary, faq, description)


def _crawlers(summary: dict, faq: list[tuple[str, str]], description: str) -> None:
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
        "> An open, reproducible study of what the world made between GTA 5 and GTA 6, how "
        "much more productive it got, and whether GTA 6 (released 19 November 2026) breaks "
        "the streak. Built with Dex.\n\n"
        f"Updated {today}. {description} "
        "Search interest, not a headcount; association, not causation.\n\n"
        f"## Questions\n\n{qa}\n\n"
        "## Links\n\n"
        f"- [Live scoreboard]({BASE})\n"
        f"- [Source code and README]({REPO})\n"
        f"- [Methodology]({REPO}/blob/main/docs/methodology.md)\n"
        f"- [Metric definitions]({REPO}/blob/main/docs/metrics.md)\n"
        f"- [Data sources]({REPO}/blob/main/docs/sources.md)\n"
        f"- [Everything we made chart data (JSON)]({BASE}charts/data/everything-we-made.json)\n"
        f"- [GTA 5 to GTA 6 chart data (JSON)]({BASE}charts/data/gta-v-to-gta-6.json)\n"
        f"- [Day-Off Index chart data (JSON)]({BASE}charts/data/day-off-index.json)\n"
        "- [Dex](https://trydex.ai)\n"
    )
