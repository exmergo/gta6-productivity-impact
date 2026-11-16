# Sources

All sources are free and public, and no API keys are needed. The ingesters are in
`src/gta6_impact/ingest/` and every pull lands as an immutable Parquet file in
`data/raw/<source>/`.

| Source | Endpoint | Granularity | Raw table |
|---|---|---|---|
| Wikipedia | `wikimedia.org/api/rest_v1/metrics/pageviews/per-article` (users, all access) | daily | `raw.wiki_pageviews` |
| Google Trends | `trendspy` (unofficial), one US request per Day-Off Index phrase over `TRENDS_SPAN` | weekly, relative 0–100 per request | `raw.trends_interest` |
| Bluesky | `api.bsky.app/xrpc/app.bsky.feed.searchPosts`, one UTC day per call, `hitsTotal` | daily count | `raw.bluesky_daily_hits` |
| Hacker News | `hn.algolia.com/api/v1/search_by_date`, `nbHits`, typo tolerance off | daily count | `raw.hn_daily_hits` |

## What we tried and dropped

- **Wikipedia hourly views.** The per-article API only serves daily and monthly data.
- **GH Archive and the ClickHouse `github_events` playground** (for the PR metric).
  Their event volume fell from about 3.5M a day to about 100k a day from late October
  2026, so a count from them can't be compared week to week. Metric 2 uses the GitHub
  Search API's `total_count` instead.

## When Google Trends rate-limits

Trends has no official API. If `gta6 ingest trends` gets a 429 response, export the
same phrases and span from trends.google.com (one phrase per export, US) and save each as
Parquet in `data/manual/trends/` with the columns `request_id, batch_id, span_start,
span_end, geo, term, day, interest, is_partial`. `gta6 load` picks it up.

Older daily, one-request-per-year pulls stay in `data/raw/trends/` as history. They carry no
span, so the index never reads them.
