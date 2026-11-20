-- Metric 5 headline: launches and comments on release day against the Thursday before, in
-- percent, one row per release day, with `breakdown` spelling out both.
select
    cast(release_day as varchar) as release_day_key,
    min(release_day) as release_day,
    min(baseline_start) as baseline_start,
    min(baseline_end) as baseline_end,
    min(baseline_weeks) as baseline_weeks,
    count(*) as activities_total,
    count(pct_change) as activities_available,
    max(pct_change) filter (where activity = 'launches') as producthunt_launches_change,
    max(pct_change) filter (where activity = 'comments') as producthunt_comments_change,
    string_agg(
        activity_label || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by activity desc
    ) as breakdown
from {{ ref('fct_producthunt_release_day_activities') }}
group by release_day
