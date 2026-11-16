# Sources

All sources are free and public, and no API keys are needed. The ingesters are in
`src/gta6_impact/ingest/` and every pull lands as an immutable Parquet file in
`data/raw/<source>/`.

| Source | Endpoint | Granularity | Raw table |
|---|---|---|---|
| Wikipedia | `wikimedia.org/api/rest_v1/metrics/pageviews/per-article` (users, all access) | daily | `raw.wiki_pageviews` |
| Google Trends | `trendspy` (unofficial) | daily, relative 0–100 per request | `raw.trends_interest` |
| Bluesky | `api.bsky.app/xrpc/app.bsky.feed.searchPosts`, one UTC day per call, `hitsTotal` | daily count | `raw.bluesky_daily_hits` |
| Hacker News | `hn.algolia.com/api/v1/search_by_date`, `nbHits`, typo tolerance off | daily count | `raw.hn_daily_hits` |
| Reddit | `arctic-shift.photon-reddit.com/api/{posts,comments}/search` | item | `raw.reddit_items` |

## What we tried and dropped

- **Wikipedia hourly views.** The per-article API only serves daily and monthly data.
- **GH Archive and the ClickHouse `github_events` playground** (for the PR metric).
  Their event volume fell from about 3.5M a day to about 100k a day from late October
  2026, so a count from them can't be compared week to week. Metric 2 uses the GitHub
  Search API's `total_count` instead.
- **Reddit's own API.** It needs OAuth, so we use the Arctic Shift archive.

## When Google Trends rate-limits

Trends has no official API. If `gta6 ingest trends` gets a 429 response, export the
same terms and window from trends.google.com and save the export as Parquet in
`data/manual/trends/` with the same columns: `request_id, term_group, geo, term, day,
interest, is_partial`. `gta6 load` picks it up.
