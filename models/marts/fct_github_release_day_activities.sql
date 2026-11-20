-- Metric 4 breakdown: one row per GitHub activity. Release day's count against the median of
-- the same weekday in each of the weeks before it (vars github_release_day and
-- github_baseline_weeks; canonical: Thu 19 Nov 2026 vs the Thursday before, 12 Nov). A median,
-- so one bulk-import spike in the commit counts cannot move a longer baseline.
{%- set release_day = var('github_release_day') %}
{%- set weeks = var('github_baseline_weeks', 1) %}
with params as (
    select
        date '{{ release_day }}' as release_day,
        cast({{ weeks }} as integer) as baseline_weeks,
        cast(date '{{ release_day }}' - 7 * {{ weeks }} as date) as baseline_start,
        cast(date '{{ release_day }}' - 7 as date) as baseline_end
),

activities as (
    select distinct activity, activity_label
    from {{ ref('fct_github_daily') }}
),

per_activity as (
    select
        activities.activity,
        activities.activity_label,
        params.release_day,
        params.baseline_weeks,
        params.baseline_start,
        params.baseline_end,
        max(daily.activity_count) filter (
            where daily.activity_date = params.release_day
        ) as release_day_count,
        median(daily.activity_count) filter (
            where daily.activity_date between params.baseline_start and params.baseline_end
                and dayofweek(daily.activity_date) = dayofweek(params.release_day)
        ) as baseline_count,
        count(daily.activity_count) filter (
            where daily.activity_date between params.baseline_start and params.baseline_end
                and dayofweek(daily.activity_date) = dayofweek(params.release_day)
        ) as baseline_days_found
    from activities
    cross join params
    left join {{ ref('fct_github_daily') }} as daily
        on activities.activity = daily.activity
    group by
        activities.activity,
        activities.activity_label,
        params.release_day,
        params.baseline_weeks,
        params.baseline_start,
        params.baseline_end
)

select
    activity,
    activity_label,
    release_day,
    baseline_weeks,
    baseline_start,
    baseline_end,
    baseline_days_found,
    baseline_count,
    release_day_count,
    case
        when release_day_count is not null
            and baseline_days_found = baseline_weeks
            and baseline_count > 0
            then 100 * (release_day_count / baseline_count - 1)
    end as pct_change
from per_activity
