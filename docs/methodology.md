# How we measure a vibe

GTA 6 comes out on Thursday 19 November 2026. Nobody publishes how many people booked
that day off. So we measure what people *search* for when they're planning to skip work,
against the same weeks a year earlier.

## The Day-Off Index

The **Day-Off Index** is the average year-over-year change in US Google searches for three
phrases:

- "call in sick"
- "sick day"
- "day off work"

For each phrase we take its average weekly search interest over a window of weeks, and the
average over the same weeks 52 weeks earlier. The phrase's change is the percent difference
between the two. The index is the plain average of the three changes.

```
change(phrase) = 100 × (avg weekly interest, current window / avg weekly interest, same weeks a year earlier − 1)
Day-Off Index  = average of change(call in sick), change(sick day), change(day off work)
```

**The index is never reported without its breakdown.** The index row carries a `breakdown`
column ("call in sick +40.4% · day off work +73.4% · sick day +36.4%"), the chart shows each
phrase beside the index, and a data test fails any row with an index and no breakdown.

### The canonical snapshot

| | |
|---|---|
| Current window | Google weeks of Sun 1 and Sun 8 Nov 2026 (1–14 Nov 2026) |
| Comparison window | Google weeks of Sun 2 and Sun 9 Nov 2025 (2–15 Nov 2025) |
| Trends request | one per phrase, US, 1 Nov 2025 – 15 Nov 2026, weekly |
| Pull | batch `20261116T185310` (16 Nov 2026, 18:53 UTC) |

| Phrase | 2025 | 2026 | Change |
|---|---|---|---|
| "call in sick" | 68.0 | 95.5 | +40.4% |
| "sick day" | 70.0 | 95.5 | +36.4% |
| "day off work" | 54.5 | 94.5 | +73.4% |
| **Day-Off Index** | | | **+50.1%** |

### Configuring the window

The window is set by dbt vars in `dbt_project.yml`:

| Var | Canonical | Meaning |
|---|---|---|
| `day_off_index_start_week` | `2026-11-01` | Sunday of the first week of the current window |
| `day_off_index_end_week` | `2026-11-08` | Sunday of the last week; `null` to use the number of weeks instead |
| `day_off_index_weeks` | `2` | Number of weeks, used when the end week is `null` |
| `day_off_index_weeks_back` | `52` | How far back the comparison window sits (52 weeks keeps Sundays aligned) |
| `day_off_index_span_start`, `_span_end` | `2025-11-01`, `2026-11-15` | The Trends request span; must cover both windows (and match `TRENDS_SPAN` in `config.py`) |
| `day_off_index_batch` | `20261116T185310` | Pin one pull; `null` reads the newest |

Unit tests in `models/marts/fct_day_off_index_terms.yml` prove the start-and-end and the
start-and-number-of-weeks settings, and that a partial week reads NULL.

## Why it's built this way

1. **One request per phrase, spanning both years.** Google Trends rescales every request
   to its own 0–100, so two numbers only compare inside one request. One request covering
   Nov 2025 to Nov 2026 puts both years on the same scale. Each phrase gets its own request
   so a heavily searched phrase can't squeeze the others toward zero.
2. **Weekly, because the span is long.** Over a span longer than about nine months Google
   answers in weeks (Sunday to Saturday), not days. Two-week windows read fine in weeks.
3. **Changes are averaged, not interest values.** Each phrase sits on its own 0–100
   scale, so the index averages the percent changes.
4. **Partial weeks don't count.** The week still in progress when the pull ran is
   flagged and left out; a window missing a week reads NULL, never a smaller number.
5. **Pulls are pinned.** Google samples: two pulls of the same request differ by a point or
   two (the canonical window moved by under one percentage point between two pulls on
   16 Nov). The published numbers come from one pinned batch, kept in `data/raw/trends/`.

## Limits

- This is search interest, not a headcount. People who quietly book PTO in an HR system
  don't search for it. The closest outside figure we know of is BambooHR's reported
  +9–17% in time-off requests for 19 Nov. That's their data, not ours.
- US only. "Call in sick" and "sick day" are US phrasing.

## Integrity rules

1. **Missing is unavailable, never zero.** A failed or partial pull leaves a gap.
2. **No people, only counts.** We store no post text, handles, usernames or URIs.
3. **Association only.** A year-over-year rise says searches were higher. It doesn't prove
   GTA caused it.

## Supporting signals

Kept outside the index, from `fct_signal_daily`:

- **GTA share of day-off talk**: Bluesky day-off posts that also say GTA, as a share of
  all day-off posts.
- **Hype**: Wikipedia daily views of *Grand Theft Auto VI*.
- **Hacker News**: the same phrases on HN. Very few matches, so it's here for the joke.
