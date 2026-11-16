"""Builds the Dex transform payload for the staging layer (kept for the audit trail)."""
import json

SOURCES_YML = """version: 2

sources:
  - name: raw
    schema: raw
    description: >
      Public signals landed by `gta6 ingest` as Parquet under data/raw/ and loaded by
      `gta6 load`. Every table is rebuilt from the files on each load; the newest pull
      wins per key. No post text, handles or usernames are stored.
    tables:
      - name: wiki_pageviews
        description: Daily English Wikipedia pageviews by users (all access) per article.
      - name: trends_interest
        description: >
          Google Trends relative interest (0-100) per term and day. Values only compare
          within one request_id; Google rescales every request to its own peak.
      - name: bluesky_daily_hits
        description: >
          Bluesky public search hitsTotal for one quoted seed phrase (optionally plus "gta")
          bounded to one UTC day. hits_total is NULL when the call failed.
      - name: hn_daily_hits
        description: >
          Hacker News (Algolia) nbHits for one quoted seed phrase (optionally plus "gta")
          over stories and comments in one UTC day. NULL when the call failed.
      - name: reddit_items
        description: >
          Reddit posts and comments (Arctic Shift archive) that matched a day-off seed in a
          tracked subreddit, with flags computed from the text at ingest. Text is discarded.
      - name: reddit_coverage
        description: >
          One row per (subreddit, kind, seed, weekly slice) we asked Arctic Shift for, with
          whether paging completed, was capped, or failed.
"""

STG_WIKI = """with source as (
    select * from {{ source('raw', 'wiki_pageviews') }}
)

select
    article,
    cast(timezone('UTC', ts) as date) as view_date,
    cast(views as bigint) as views
from source
where granularity = 'daily'
"""

STG_TRENDS = """-- Each Trends request is scaled to its own 0-100, so we keep exactly one request per
-- (term group, geo, study year): the newest. Mixing requests would mix scales.
with source as (
    select
        *,
        cast(split_part(request_id, '-', 3) as integer) as study_year
    from {{ source('raw', 'trends_interest') }}
),

newest as (
    select term_group, geo, study_year, max(request_id) as request_id
    from source
    group by term_group, geo, study_year
)

select
    source.request_id,
    source.study_year,
    source.term_group,
    source.geo,
    source.term,
    source.day as interest_date,
    cast(source.interest as integer) as interest,
    source.is_partial
from source
inner join newest
    on source.request_id = newest.request_id
"""

STG_BSKY = """select
    day as hit_date,
    seed,
    gta_filter,
    query,
    cast(hits_total as bigint) as hits_total,
    hits_total is not null as is_available,
    observed_at
from {{ source('raw', 'bluesky_daily_hits') }}
"""

STG_HN = """select
    day as hit_date,
    seed,
    gta_filter,
    query,
    cast(hits_total as bigint) as hits_total,
    hits_total is not null as is_available,
    observed_at
from {{ source('raw', 'hn_daily_hits') }}
"""

STG_REDDIT = """select
    kind || ':' || item_id as reddit_item_key,
    item_id,
    kind,
    lower(subreddit) as subreddit,
    created_at,
    cast(timezone('UTC', created_at) as date) as created_date,
    mentions_day_off,
    mentions_gta
from {{ source('raw', 'reddit_items') }}
"""

STG_REDDIT_COV = """select
    lower(subreddit) as subreddit,
    kind,
    seed,
    slice_start,
    slice_end,
    status,
    status = 'complete' as is_complete,
    pages,
    items_matched
from {{ source('raw', 'reddit_coverage') }}
"""

edits = [
    {"path": "models/staging/_sources.yml", "kind": "schema_yml", "content": SOURCES_YML},
    {"path": "models/staging/stg_wiki__pageviews.sql", "kind": "model_sql", "content": STG_WIKI},
    {"path": "models/staging/stg_trends__interest.sql", "kind": "model_sql", "content": STG_TRENDS},
    {"path": "models/staging/stg_bluesky__daily_hits.sql", "kind": "model_sql", "content": STG_BSKY},
    {"path": "models/staging/stg_hn__daily_hits.sql", "kind": "model_sql", "content": STG_HN},
    {"path": "models/staging/stg_reddit__items.sql", "kind": "model_sql", "content": STG_REDDIT},
    {"path": "models/staging/stg_reddit__coverage.sql", "kind": "model_sql", "content": STG_REDDIT_COV},
]

daily_hits_cols = lambda src: {
    "hit_date": {"role": "time", "null_rule": "never", "description": "UTC day the count covers."},
    "seed": {"role": "dimension", "null_rule": "never", "description": "Day-off seed phrase searched, quoted."},
    "gta_filter": {"role": "dimension", "null_rule": "never", "description": "'any' = the phrase alone; 'gta' = the phrase plus the word gta."},
    "query": {"role": "attribute", "description": "The exact query string sent."},
    "hits_total": {"role": "measure", "aggregation": "sum", "additivity": "additive", "unit": "count",
                    "null_rule": f"NULL when the {src} call failed: unavailable, never zero.",
                    "description": f"Matches {src} reports for the query in that UTC day."},
    "is_available": {"role": "attribute", "null_rule": "never", "description": "True when hits_total was returned."},
    "observed_at": {"role": "attribute", "description": "When the count was read (counts can move as indexes update)."},
}

declarations = [
    {"model": "stg_wiki__pageviews",
     "description": "One row per Wikipedia article per UTC day: daily user pageviews.",
     "grain": ["article", "view_date"],
     "population": {"rule": "Daily-granularity rows only; the per-article API serves no hourly data.",
                    "filters": [{"column": "granularity", "includes": ["daily"]}]},
     "columns": {
         "article": {"role": "dimension", "null_rule": "never", "description": "English Wikipedia article title."},
         "view_date": {"role": "time", "null_rule": "never", "description": "UTC day. The raw ts is a UTC midnight stored as TIMESTAMPTZ; converted explicitly so the session time zone cannot shift it."},
         "views": {"role": "measure", "aggregation": "sum", "additivity": "additive", "unit": "count", "null_rule": "never", "description": "Pageviews by users (agent=user), all access methods."}},
     "assumptions": [{"decision": "Which day a timestamp belongs to", "chosen": "the UTC date of ts", "evidence": "data",
                      "detail": "explore showed ts rendered at +01:00/+02:00 in a local session; the API's timestamps are UTC midnights"}]},
    {"model": "stg_trends__interest",
     "description": "One row per Trends term per day, from the newest request for each (term group, geo, study year).",
     "grain": ["term_group", "geo", "study_year", "term", "interest_date"],
     "population": {"rule": "Only the newest request per (term_group, geo, study_year); older pulls are dropped because each request has its own 0-100 scale."},
     "columns": {
         "request_id": {"role": "attribute", "null_rule": "never", "description": "The Trends request the value came from; values only compare within one request."},
         "study_year": {"role": "dimension", "null_rule": "never", "description": "2026 = study window, 2025 = seasonality control."},
         "term_group": {"role": "dimension", "null_rule": "never", "description": "'day_off' (call in sick, sick day, PTO, day off work) or 'hype' (GTA 6). Requested separately."},
         "geo": {"role": "dimension", "null_rule": "never", "description": "'US' or 'WORLD'."},
         "term": {"role": "dimension", "null_rule": "never", "description": "The search term."},
         "interest_date": {"role": "time", "null_rule": "never", "description": "The day Google reports, in Google's own day boundaries."},
         "interest": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "index (0-100, relative within request)", "null_rule": "never", "description": "Relative search interest; 100 is the peak of that request."},
         "is_partial": {"role": "attribute", "null_rule": "never", "description": "Google marks the latest day partial while it is still filling in."}},
     "assumptions": [
         {"decision": "How to combine repeated Trends pulls", "chosen": "keep only the newest request per (term_group, geo, study_year)", "evidence": "default",
          "detail": "Trends rescales each request; averaging requests would mix scales"},
         {"decision": "Study year source", "chosen": "third dash-separated part of request_id", "evidence": "contract",
          "detail": "request_id is written as <group>-<geo>-<year>-<stamp> by gta6_impact.ingest.trends"}]},
    {"model": "stg_bluesky__daily_hits",
     "description": "One row per Bluesky search (seed phrase x gta filter) per UTC day: the hitsTotal Bluesky reported.",
     "grain": ["hit_date", "seed", "gta_filter"],
     "population": {"rule": "Every query we asked, including failed ones (hits_total NULL)."},
     "columns": daily_hits_cols("Bluesky")},
    {"model": "stg_hn__daily_hits",
     "description": "One row per Hacker News search (seed phrase x gta filter) per UTC day: Algolia's nbHits over stories and comments.",
     "grain": ["hit_date", "seed", "gta_filter"],
     "population": {"rule": "Every query we asked, including failed ones (hits_total NULL)."},
     "columns": daily_hits_cols("Hacker News")},
    {"model": "stg_reddit__items",
     "description": "One row per Reddit post or comment that matched a day-off seed in a tracked subreddit.",
     "grain": ["reddit_item_key"],
     "population": {"rule": "Items returned by Arctic Shift full-text search for any seed in the tracked subreddits and weekly slices; the text itself is discarded at ingest."},
     "columns": {
         "reddit_item_key": {"role": "key", "null_rule": "never", "description": "kind:item_id; post and comment ids are separate id spaces."},
         "item_id": {"role": "attribute", "null_rule": "never", "description": "Reddit's base-36 id."},
         "kind": {"role": "dimension", "null_rule": "never", "description": "'post' or 'comment'."},
         "subreddit": {"role": "dimension", "null_rule": "never", "description": "Lower-cased subreddit name."},
         "created_at": {"role": "time", "null_rule": "never", "description": "Creation time, UTC."},
         "created_date": {"role": "time", "null_rule": "never", "description": "UTC day of creation."},
         "mentions_day_off": {"role": "dimension", "null_rule": "never", "description": "The text matched a day-off phrase on whole words (search matches can be looser)."},
         "mentions_gta": {"role": "dimension", "null_rule": "never", "description": "The text mentioned GTA (gta, gta 6, gta vi, grand theft auto)."}}},
    {"model": "stg_reddit__coverage",
     "description": "One row per (subreddit, kind, seed, weekly slice) requested from Arctic Shift, and whether paging completed.",
     "grain": ["subreddit", "kind", "seed", "slice_start"],
     "population": {"rule": "Every slice requested; the newest complete attempt wins at load."},
     "columns": {
         "subreddit": {"role": "dimension", "null_rule": "never"},
         "kind": {"role": "dimension", "null_rule": "never"},
         "seed": {"role": "dimension", "null_rule": "never"},
         "slice_start": {"role": "time", "null_rule": "never", "description": "Slice start, inclusive (UTC date)."},
         "slice_end": {"role": "time", "null_rule": "never", "description": "Slice end, exclusive (UTC date)."},
         "status": {"role": "dimension", "null_rule": "never", "description": "complete, capped (hit the page limit) or failed."},
         "is_complete": {"role": "attribute", "null_rule": "never"},
         "pages": {"role": "measure", "aggregation": "sum", "additivity": "additive", "unit": "count"},
         "items_matched": {"role": "measure", "aggregation": "sum", "additivity": "additive", "unit": "count"}}},
]

json.dump({"edits": edits, "declarations": declarations}, open("01-staging.json", "w"), indent=1)
print("wrote 01-staging.json")
