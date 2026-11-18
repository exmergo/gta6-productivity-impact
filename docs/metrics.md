# The series

GTA 6 against the economy, one Thursday at a time. Every metric uses the same pipeline:
ingest, `raw`, staging, intermediate, marts, MetricFlow, then a chart drawn from a
semantic query.

| # | Metric | Question | Source | Status |
|---|---|---|---|---|
| 1 | **Day-Off Index** | Are people searching for ways to skip work more than last year? | Google Trends, US, weekly | live |
| 2 | **GTA 5 to GTA 6** | How much more productive did the world get between the two launches? | World Bank WDI (world GDP per person employed and per capita, real), IMF WEO for 2026 | live |
| 3 | **Everything humanity made while waiting** | How much did the world make between GTA 5 and GTA 6? | World Bank WDI (world GDP, real), IMF WEO for 2026, a seed of milestones | live (release day, Thu 19 Nov) |
| 4 | **PRs opened** | Did GitHub go quiet? | GitHub Search API, `is:pr created:<day>` | Fri 20 Nov |
| 5 | **Wikipedia brain drain** | Did the world stop editing the encyclopaedia? | Wikimedia `edits/aggregate` | after release |
| 6 | **The recovery curve** | How many working days until output is back to normal? | Metrics 4–5, daily for two weeks | 30 Nov |

## 2. GTA 5 to GTA 6

World productivity between the two launches, from official economic data only:
GTA 5 came out in 2013, GTA 6 comes out in 2026, and the metric is the real change in
between.

- **Output per worker**: world GDP per person employed, constant 2021 PPP dollars
  (World Bank `SL.GDP.PCAP.EM.KD`).
- **Output per person**: world GDP per capita, constant 2015 US dollars (World Bank
  `NY.GDP.PCAP.KD`).
- **2026**: the World Bank series end at the last published year (2025). GDP per capita
  for 2026 is 2025 grown by the IMF World Economic Outlook's 2026 world real GDP growth
  (`NGDP_RPCH`) less world population growth (`SP.POP.GROW`, last published year), and is
  labelled as an estimate. Output per worker stops at the last published year.

| World, real | 2013 (GTA 5) | Latest | Change |
|---|---|---|---|
| GDP per person (constant 2015 US$) | $9,811 | $12,394 (2026, estimate) | **+26.3%** |
| GDP per worker (constant 2021 PPP $) | $40,581 | $50,672 (2025) | **+24.9%** |

Ask it: `uv run dex explore semantic query world_productivity_change_since_gta_v,world_productivity
--group-by world_productivity_key__measure,world_productivity_key__data_year`. Model:
`fct_world_productivity` (one row per measure per year; the IMF chain is unit-tested, including a
missing IMF year leaving the value NULL). Charts: `charts/png/gta-v-to-gta-6-{light,dark}.png` and the 4:5 `gta-v-to-gta-6-portrait-{light,dark}.png`.

## 3. Everything humanity made while waiting

Everything the world made between GTA 5 and GTA 6, as real output, with the moments in between
placed on the running total.

- **The wait**: every UTC day from GTA 5's release (17 Sep 2013, inclusive) to the day before
  GTA 6 (18 Nov 2026, inclusive): 4,811 days. GTA 6 unlocks at 19 Nov 2026 00:00 UTC, the
  moment the scoreboard's countdown and ticker use. dbt vars `gta_v_date` and `gta_6_date`.
- **World output**: world GDP, constant 2015 US dollars at market exchange rates (World Bank
  `NY.GDP.MKTP.KD`), the same price basis as Metric 2's per-capita series.
- **Daily output**: a year's GDP divided by its days (365 or 366), spread evenly. No
  seasonality is claimed, and the per-second rate is that daily figure over 86,400.
- **2026**: the World Bank's 2025 GDP grown by the IMF World Economic Outlook's 2026 world real
  GDP growth (`NGDP_RPCH`), labelled as an estimate. Total output takes no population
  adjustment. A missing IMF year would leave that year and every later one NULL (unit-tested).
- **Running total**: the sum of daily output from 17 Sep 2013 through the day. It is never
  summed across days; `world_output_produced` with no group-by is the headline.
- **Milestones**: not a ranking (`seeds/wait_milestones.csv`, 46 rows). Each is
  dated to a UTC day against one public source, and reads the running total through the day
  *before* it ("by the time it happened, the world had made $X since GTA 5"). GTA 5's own day
  reads $0. The nine `is_editorial` rows are on the chart as picture cards (filter
  `milestone__is_editorial = true`), every row is on the scoreboard table, and the two Rockstar
  nods (Red Dead Redemption 2, GTA 6 Trailer 1) are drawn as stars with ink cards. Each card
  carries its picture (`brand/milestones/`), the year and the chart label.

**$1.14 quadrillion** ($1,141.7T) in 4,811 days. In 2026 the world makes about $3.3 million a
second, or $282 billion a day.

| Year | Made in the wait | Running total since GTA 5 |
|---|---|---|
| 2013 | $20.7T | $20.7T |
| 2014 | $73.5T | $94.2T |
| 2015 | $75.8T | $170.1T |
| 2016 | $78.0T | $248.0T |
| 2017 | $80.6T | $328.7T |
| 2018 | $83.3T | $412.0T |
| 2019 | $85.5T | $497.5T |
| 2020 | $83.1T | $580.6T |
| 2021 | $88.4T | $669.0T |
| 2022 | $91.5T | $760.5T |
| 2023 | $94.1T | $854.6T |
| 2024 | $96.8T | $951.4T |
| 2025 | $99.7T | $1,051.1T |
| 2026 (estimate) | $90.6T | $1,141.7T |

Generated from `world_output_produced` by `world_output_day__data_year` and
`world_output_cumulative` by `metric_time__year`.

Limits: it's real GDP at 2015 prices, not wellbeing and not today's dollars (a nominal figure
would be larger). 2026 is an estimate, and the IMF growth rate is PPP-weighted while the World
Bank series uses market exchange rates (the same caveat as Metric 2). The milestones are
editorial; each row carries its source.

Ask it: `uv run dex explore semantic query world_output_produced` and
`uv run dex explore semantic query wait_milestone_output --group-by milestone__title,milestone__event_date`.
Models: `int_world_output__yearly` (one row per year, unit-tested and mutation-tested),
`fct_world_output_daily` (one row per day of the wait) and `fct_wait_milestones` (one row per
milestone, driven from the seed). Charts: `charts/png/everything-we-made-{light,dark}.png` and the
4:5 `everything-we-made-portrait-{light,dark}.png`; the scoreboard's ticker reads
`world_output_per_second` for the last day of the wait.
