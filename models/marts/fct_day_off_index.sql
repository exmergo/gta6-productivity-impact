-- The Day-Off Index: the average of the three phrases' year-over-year changes, in percent,
-- one row per window. It always carries its breakdown: `breakdown` spells out every phrase's
-- change, so the index is never read without it.
with terms as (
    select
        *,
        cast(current_start_week as varchar) || '/' || cast(current_end_week as varchar)
            as index_window
    from {{ ref('fct_day_off_index_terms') }}
)

select
    index_window,
    min(current_start_week) as current_start_week,
    min(current_end_week) as current_end_week,
    min(prior_start_week) as prior_start_week,
    min(prior_end_week) as prior_end_week,
    min(weeks) as weeks,
    max(batch_id) as batch_id,
    count(*) as phrase_count,
    count(pct_change) as phrases_available,
    case when count(pct_change) = count(*) then avg(pct_change) end as day_off_index,
    string_agg(
        term || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by term
    ) as breakdown
from terms
group by index_window
