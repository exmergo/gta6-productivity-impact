-- Metric 4: GitHub activity per UTC day. One row per day per activity, for every day asked
-- for (release day, the weeks before it and the weeks after it).
{%- set release_day = var('github_release_day') %}
select
    md5(activity || '|' || cast(activity_date as varchar)) as github_day_key,
    activity_date,
    activity,
    case activity
        when 'prs_opened' then 'PRs opened'
        when 'prs_merged' then 'PRs merged'
        when 'commits' then 'Commits'
        else activity
    end as activity_label,
    activity_count,
    is_available,
    dayname(activity_date) as weekday_name,
    activity_date = date '{{ release_day }}' as is_release_day,
    cast(date_diff('day', date '{{ release_day }}', activity_date) as integer)
        as days_from_release,
    observed_at
from {{ ref('stg_github__daily_counts') }}
