# The series

GTA 6 against the economy, one Thursday at a time. Every metric uses the same pipeline:
ingest, `raw`, staging, intermediate, marts, MetricFlow, then a chart drawn from a
semantic query.

| # | Metric | Question | Source | Status |
|---|---|---|---|---|
| 1 | **Day-Off Index** | Are people searching for ways to skip work more than last year? | Google Trends, US, weekly | live |
| 2 | **PRs opened** | Did GitHub go quiet? | GitHub Search API, `is:pr created:<day>` | after release |
| 3 | **Stack Overflow silence** | Did developers stop asking questions? | Stack Exchange API, `filter=total` | after release |
| 4 | **Wikipedia brain drain** | Did the world stop editing the encyclopaedia? | Wikimedia `edits/aggregate` | after release |
| 5 | **The recovery curve** | How many working days until output is back to normal? | Metrics 2–4, daily for two weeks | 30 Nov |
