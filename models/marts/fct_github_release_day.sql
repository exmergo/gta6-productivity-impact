-- Metric 4 headline: the average of the activities' release-day changes, in percent, one row
-- per release day. It always carries its breakdown: `breakdown` spells out every activity's
-- change, so the headline is never read without it.
select
    cast(release_day as varchar) as release_day_key,
    min(release_day) as release_day,
    min(baseline_start) as baseline_start,
    min(baseline_end) as baseline_end,
    min(baseline_weeks) as baseline_weeks,
    count(*) as activities_total,
    count(pct_change) as activities_available,
    case when count(pct_change) = count(*) then avg(pct_change) end as github_release_day_change,
    string_agg(
        activity_label || ' ' || coalesce(printf('%+.1f%%', pct_change), 'not yet available'),
        ' · ' order by activity desc
    ) as breakdown
from {{ ref('fct_github_release_day_activities') }}
group by release_day
