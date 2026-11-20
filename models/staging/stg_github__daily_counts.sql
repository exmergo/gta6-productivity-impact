-- One row per UTC day per GitHub activity, from one GitHub Search API call each (Metric 4).
-- activity_count is NULL when the call failed or GitHub flagged the result incomplete:
-- unavailable, never zero.
select
    cast(day as date) as activity_date,
    activity,
    endpoint,
    query,
    case
        when total_count is not null and not coalesce(incomplete_results, true)
            then cast(total_count as bigint)
    end as activity_count,
    total_count is not null and not coalesce(incomplete_results, true) as is_available,
    observed_at
from {{ source('raw', 'github_daily_counts') }}
