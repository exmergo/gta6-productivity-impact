# The series

GTA 6 against the economy, one Thursday at a time. Every metric uses the same pipeline:
ingest, `raw`, staging, intermediate, marts, MetricFlow, then a chart drawn from a
semantic query.

| # | Metric | Question | Source | Status |
|---|---|---|---|---|
| 1 | **Day-Off Index** | Are people searching for ways to skip work more than last year? | Google Trends, US, weekly | live |
| 2 | **GTA V to GTA 6** | How much more productive did the world get between the two launches? | World Bank WDI (world GDP per person employed and per capita, real), IMF WEO for 2026 | Wed 18 Nov |
| 3 | **PRs opened** | Did GitHub go quiet? | GitHub Search API, `is:pr created:<day>` | after release |
| 4 | **Wikipedia brain drain** | Did the world stop editing the encyclopaedia? | Wikimedia `edits/aggregate` | after release |
| 5 | **The recovery curve** | How many working days until output is back to normal? | Metrics 3–4, daily for two weeks | 30 Nov |

## 2. GTA V to GTA 6

World productivity between the two launches, from official economic data only:
GTA V came out in 2013, GTA 6 comes out in 2026, and the metric is the real change in
between.

- **Output per worker**: world GDP per person employed, constant 2021 PPP dollars
  (World Bank `SL.GDP.PCAP.EM.KD`).
- **Output per person**: world GDP per capita, constant 2015 US dollars (World Bank
  `NY.GDP.PCAP.KD`).
- **2026**: the World Bank series end at the last published year (2025). GDP per capita
  for 2026 is 2025 grown by the IMF World Economic Outlook's 2026 world real GDP growth
  (`NGDP_RPCH`) less world population growth (`SP.POP.GROW`, last published year), and is
  labelled as an estimate. Output per worker stops at the last published year.
