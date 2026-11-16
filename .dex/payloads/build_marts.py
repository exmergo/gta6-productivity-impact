"""Builds the Dex transform payload for the intermediate and mart layers."""
import json

INT_SIGNALS = """-- Every signal as one daily value per (source, signal, geo, UTC day).
-- A value that could not be read is NULL with is_available = false: unavailable, never zero.
with trends as (
    select
        'google_trends' as source,
        'search:' || lower(term) as signal,
        case term_group when 'day_off' then 'day_off_intent' else 'hype' end as signal_family,
        geo,
        interest_date as signal_date,
        case when not is_partial then cast(interest as double) end as signal_value,
        not is_partial as is_available
    from {{ ref('stg_trends__interest') }}
),

bluesky as (
    select
        'bluesky' as source,
        case gta_filter when 'gta' then 'posts:day_off_gta' else 'posts:day_off' end as signal,
        case gta_filter when 'gta' then 'day_off_gta' else 'day_off_intent' end as signal_family,
        'WORLD' as geo,
        hit_date as signal_date,
        case when bool_and(is_available) then cast(sum(hits_total) as double) end as signal_value,
        bool_and(is_available) as is_available
    from {{ ref('stg_bluesky__daily_hits') }}
    group by gta_filter, hit_date
),

hacker_news as (
    select
        'hacker_news' as source,
        case gta_filter when 'gta' then 'posts:day_off_gta' else 'posts:day_off' end as signal,
        case gta_filter when 'gta' then 'day_off_gta' else 'day_off_intent' end as signal_family,
        'WORLD' as geo,
        hit_date as signal_date,
        case when bool_and(is_available) then cast(sum(hits_total) as double) end as signal_value,
        bool_and(is_available) as is_available
    from {{ ref('stg_hn__daily_hits') }}
    group by gta_filter, hit_date
),

wikipedia as (
    select
        'wikipedia' as source,
        'pageviews:' || lower(article) as signal,
        case when article = 'Grand_Theft_Auto_VI' then 'hype' else 'reference' end as signal_family,
        'WORLD' as geo,
        view_date as signal_date,
        cast(views as double) as signal_value,
        true as is_available
    from {{ ref('stg_wiki__pageviews') }}
)

select * from trends
union all
select * from bluesky
union all
select * from hacker_news
union all
select * from wikipedia
"""

DIM_DATE = """-- One row per UTC day of the study window and its control year, with its place relative
-- to that year's release Thursday.
with spine as (
    select cast(range as date) as date_day
    from range(date '2025-10-01', date '2027-01-01', interval 1 day)
),

years as (
    select
        date_day,
        case when date_day >= date '2026-01-01' then 2026 else 2025 end as study_year
    from spine
),

anchored as (
    select
        date_day,
        study_year,
        case study_year when 2026 then date '2026-11-19' else date '2025-11-20' end as release_day
    from years
)

select
    date_day,
    study_year,
    release_day,
    cast(date_day - release_day as integer) as days_from_release,
    isodow(date_day) as iso_day_of_week,
    dayname(date_day) as day_name,
    case cast(date_day - release_day as integer)
        when 0 then 'release'
        when -7 then 'baseline'
    end as comparison_role,
    study_year = 2026 and date_day = release_day as is_gta_release_day
from anchored
"""

FCT_SIGNAL_DAILY = """select
    md5(
        signals.source || '|' || signals.signal || '|' || signals.geo || '|'
        || cast(signals.signal_date as varchar)
    ) as signal_day_key,
    signals.source,
    signals.signal,
    signals.signal_family,
    signals.geo,
    signals.signal_date,
    signals.signal_value,
    signals.is_available,
    dates.study_year,
    dates.days_from_release,
    dates.iso_day_of_week,
    dates.comparison_role
from {{ ref('int_signals__daily') }} as signals
inner join {{ ref('dim_date') }} as dates
    on signals.signal_date = dates.date_day
"""

FCT_THURSDAY_LIFT = """-- Release Thursday over the Thursday before, per signal and study year.
with pairs as (
    select
        source,
        signal,
        signal_family,
        geo,
        study_year,
        max(signal_value) filter (where comparison_role = 'baseline') as baseline_value,
        max(signal_value) filter (where comparison_role = 'release') as release_value,
        coalesce(bool_or(is_available) filter (where comparison_role = 'baseline'), false)
            as is_baseline_available,
        coalesce(bool_or(is_available) filter (where comparison_role = 'release'), false)
            as is_release_available
    from {{ ref('fct_signal_daily') }}
    where comparison_role is not null
    group by source, signal, signal_family, geo, study_year
)

select
    md5(source || '|' || signal || '|' || geo || '|' || cast(study_year as varchar))
        as thursday_lift_key,
    source,
    signal,
    signal_family,
    geo,
    study_year,
    case study_year when 2026 then date '2026-11-19' else date '2025-11-20' end as release_day,
    baseline_value,
    release_value,
    is_baseline_available,
    is_release_available,
    case
        when is_baseline_available and is_release_available and baseline_value > 0
            then release_value / baseline_value
    end as lift,
    signal_family = 'day_off_intent'
    and source in ('google_trends', 'bluesky', 'reddit')
    and (source <> 'google_trends' or baseline_value >= 5) as is_index_component
from pairs
"""

FCT_INDEX = """-- The Day-Off Index: geometric mean of per-source lifts (each source the geometric mean of
-- its own component signals), x 100. 100 is a normal week.
with components as (
    select * from {{ ref('fct_thursday_lift') }}
    where is_index_component
),

by_source as (
    select
        study_year,
        source,
        count(*) as signals_total,
        count(lift) as signals_with_lift,
        case
            when count(lift) = count(*) then exp(avg(ln(greatest(lift, 0.01))))
        end as source_lift
    from components
    group by study_year, source
)

select
    study_year,
    case study_year when 2026 then date '2026-11-19' else date '2025-11-20' end as release_day,
    count(*) as sources_total,
    count(source_lift) as sources_with_lift,
    case
        when count(source_lift) = count(*) then 100 * exp(avg(ln(source_lift)))
    end as day_off_index,
    max(case when source = 'google_trends' then source_lift end) as google_trends_lift,
    max(case when source = 'bluesky' then source_lift end) as bluesky_lift,
    max(case when source = 'reddit' then source_lift end) as reddit_lift
from by_source
group by study_year
"""

edits = [
    {"path": "models/intermediate/int_signals__daily.sql", "kind": "model_sql", "content": INT_SIGNALS},
    {"path": "models/marts/dim_date.sql", "kind": "model_sql", "content": DIM_DATE},
    {"path": "models/marts/fct_signal_daily.sql", "kind": "model_sql", "content": FCT_SIGNAL_DAILY},
    {"path": "models/marts/fct_thursday_lift.sql", "kind": "model_sql", "content": FCT_THURSDAY_LIFT},
    {"path": "models/marts/fct_day_off_index.sql", "kind": "model_sql", "content": FCT_INDEX},
]

signal_cols = {
    "source": {"role": "dimension", "null_rule": "never", "description": "google_trends, bluesky, reddit, hacker_news or wikipedia."},
    "signal": {"role": "dimension", "null_rule": "never", "description": "What is counted, e.g. search:pto, posts:day_off, posts:day_off_gta, pageviews:grand_theft_auto_vi."},
    "signal_family": {"role": "dimension", "null_rule": "never", "description": "day_off_intent (people saying or searching they are off), day_off_gta (the same, mentioning GTA), hype (interest in GTA itself), reference."},
    "geo": {"role": "dimension", "null_rule": "never", "description": "US or WORLD. Only Google Trends has a US slice."},
    "signal_date": {"role": "time", "null_rule": "never", "description": "UTC day (Google's own day for Trends)."},
    "signal_value": {"role": "measure", "aggregation": "sum", "additivity": "non_additive", "unit": "count or index (see signal)",
                      "null_rule": "NULL when the value could not be read: unavailable, never zero.",
                      "description": "Counts for posts and pageviews; relative 0-100 interest for Trends. Never add across signals or sources."},
    "is_available": {"role": "attribute", "null_rule": "never", "description": "False when any part of the day's value failed to load or was partial."},
}

declarations = [
    {"model": "int_signals__daily",
     "description": "One row per signal per day: every source's daily value in one shape.",
     "grain": ["source", "signal", "geo", "signal_date"],
     "population": {"rule": "Every staged day of every source; Bluesky and Hacker News seeds are summed per day and filter."},
     "columns": signal_cols,
     "assumptions": [
         {"decision": "Combining seed phrases", "chosen": "sum hits across seeds per day", "evidence": "default",
          "detail": "a post matching two seeds counts twice; the double count is the same on both Thursdays, so the lift is unaffected in expectation"},
         {"decision": "A partial or failed day", "chosen": "signal_value NULL, is_available false", "evidence": "request",
          "detail": "docs/methodology.md: missing is unavailable, never zero"},
         {"decision": "Trends partial days", "chosen": "treated as unavailable", "evidence": "default",
          "detail": "Google flags the latest day isPartial while it fills in"}]},
    {"model": "dim_date",
     "description": "One row per UTC day from 2025-10-01 to 2026-12-31, placed relative to that year's release Thursday.",
     "grain": ["date_day"],
     "population": {"rule": "Every calendar day in the spine; 2025 days belong to the control year (anchor Thu 20 Nov 2025), 2026 days to the study (anchor Thu 19 Nov 2026)."},
     "columns": {
         "date_day": {"role": "key", "null_rule": "never"},
         "study_year": {"role": "dimension", "null_rule": "never", "description": "2026 = GTA 6 release year; 2025 = seasonality control."},
         "release_day": {"role": "attribute", "null_rule": "never", "description": "That year's anchor Thursday."},
         "days_from_release": {"role": "dimension", "null_rule": "never", "unit": "days", "description": "0 on the anchor Thursday, -7 on the baseline Thursday."},
         "iso_day_of_week": {"role": "dimension", "null_rule": "never", "description": "1 = Monday ... 7 = Sunday."},
         "day_name": {"role": "attribute", "null_rule": "never"},
         "comparison_role": {"role": "dimension", "null_rule": "NULL on days that are neither Thursday of the comparison", "description": "'release' or 'baseline'."},
         "is_gta_release_day": {"role": "dimension", "null_rule": "never"}},
     "assumptions": [{"decision": "Control anchor", "chosen": "Thu 20 Nov 2025 vs Thu 13 Nov 2025", "evidence": "request",
                      "detail": "same week of November, one year earlier, both a week before US Thanksgiving week"}]},
    {"model": "fct_signal_daily",
     "description": "One row per signal per UTC day inside the study and control windows, with its place relative to release.",
     "grain": ["signal_day_key"],
     "population": {"rule": "Signal-days whose date falls in dim_date; days outside the spine are dropped by the inner join.",
                    "parent": {"model": "int_signals__daily", "key": {"source": "source", "signal": "signal", "geo": "geo", "signal_date": "signal_date"}}},
     "columns": dict(signal_cols, **{
         "signal_day_key": {"role": "key", "null_rule": "never", "description": "md5 of source|signal|geo|signal_date."},
         "study_year": {"role": "dimension", "null_rule": "never"},
         "days_from_release": {"role": "dimension", "null_rule": "never", "unit": "days"},
         "iso_day_of_week": {"role": "dimension", "null_rule": "never"},
         "comparison_role": {"role": "dimension", "null_rule": "NULL except on the two compared Thursdays"}}),
     "assumptions": [{"decision": "Days outside the window", "chosen": "dropped", "evidence": "default", "column": "signal_date",
                      "detail": "the inner join to dim_date is a filter on the study spine"}]},
    {"model": "fct_thursday_lift",
     "description": "One row per signal per study year: the release Thursday's value over the Thursday before.",
     "grain": ["thursday_lift_key"],
     "population": {"rule": "Every (source, signal, geo, study year) that has a row on either compared Thursday."},
     "columns": {
         "thursday_lift_key": {"role": "key", "null_rule": "never"},
         "source": {"role": "dimension", "null_rule": "never"},
         "signal": {"role": "dimension", "null_rule": "never"},
         "signal_family": {"role": "dimension", "null_rule": "never"},
         "geo": {"role": "dimension", "null_rule": "never"},
         "study_year": {"role": "dimension", "null_rule": "never"},
         "release_day": {"role": "time", "null_rule": "never"},
         "baseline_value": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "count or index", "null_rule": "NULL when the baseline Thursday is not available"},
         "release_value": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "count or index", "null_rule": "NULL until the release Thursday has closed and loaded"},
         "is_baseline_available": {"role": "attribute", "null_rule": "never"},
         "is_release_available": {"role": "attribute", "null_rule": "never"},
         "lift": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "ratio",
                  "null_rule": "NULL unless both Thursdays are available and the baseline is above zero", "description": "release_value / baseline_value. 1.0 = a normal week."},
         "is_index_component": {"role": "dimension", "null_rule": "never", "description": "True for the day-off intent signals of Google Trends (baseline >= 5), Bluesky and Reddit."}},
     "assumptions": [
         {"decision": "Index components", "chosen": "day_off_intent signals of google_trends, bluesky and reddit", "evidence": "request",
          "detail": "Hacker News is too sparse (334 hits in 107 days, .dex/review/05); Wikipedia is hype or reference only"},
         {"decision": "Low-resolution Trends terms", "chosen": "excluded from the index when the baseline is below 5", "evidence": "data",
          "detail": "Trends rounds to integers; a baseline of 1-4 turns a one-point wobble into a 25-100% lift"}]},
    {"model": "fct_day_off_index",
     "description": "One row per study year: the Day-Off Index and each source's lift.",
     "grain": ["study_year"],
     "population": {"rule": "Study years with at least one index component."},
     "columns": {
         "study_year": {"role": "key", "null_rule": "never"},
         "release_day": {"role": "time", "null_rule": "never"},
         "sources_total": {"role": "attribute", "null_rule": "never", "unit": "count"},
         "sources_with_lift": {"role": "attribute", "null_rule": "never", "unit": "count"},
         "day_off_index": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "index (100 = normal week)",
                           "null_rule": "NULL until every component source has a lift"},
         "google_trends_lift": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "ratio"},
         "bluesky_lift": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "ratio"},
         "reddit_lift": {"role": "measure", "aggregation": "max", "additivity": "non_additive", "unit": "ratio"}},
     "assumptions": [
         {"decision": "How lifts combine", "chosen": "geometric mean within each source, then across sources, equal weights", "evidence": "default",
          "detail": "lifts are ratios; the geometric mean keeps one noisy source from dominating"},
         {"decision": "A zero lift", "chosen": "floored at 0.01 before the log", "evidence": "default",
          "detail": "ln(0) is undefined; a component that fell to zero still pulls the index down hard"},
         {"decision": "Incomplete index", "chosen": "NULL until every component source has a lift", "evidence": "request",
          "detail": "missing is unavailable, never zero"}]},
]

json.dump({"edits": edits, "declarations": declarations}, open("02-marts.json", "w"), indent=1)
print("ok")
