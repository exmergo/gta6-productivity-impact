-- Metric 4: GitHub activity per UTC day. One row per day per activity, for every day asked
-- for (release day, the weeks before it and the weeks after it), with the same weekday a week
-- earlier beside it (a date join, not a row offset, so a missing day cannot shift the pairing).
{%- set release_day = var('github_release_day') %}
with daily as (
    select * from {{ ref('stg_github__daily_counts') }}
)

select
    md5(daily.activity || '|' || cast(daily.activity_date as varchar)) as github_day_key,
    daily.activity_date,
    daily.activity,
    case daily.activity
        when 'prs_opened' then 'PRs opened'
        when 'prs_merged' then 'PRs merged'
        when 'commits' then 'Commits'
        else daily.activity
    end as activity_label,
    daily.activity_count,
    daily.is_available,
    dayname(daily.activity_date) as weekday_name,
    daily.activity_date = date '{{ release_day }}' as is_release_day,
    cast(date_diff('day', date '{{ release_day }}', daily.activity_date) as integer)
        as days_from_release,
    daily.observed_at,
    week_before.activity_count as prior_week_count,
    case
        when daily.activity_count is not null and week_before.activity_count > 0
            then 100 * (daily.activity_count / week_before.activity_count - 1)
    end as wow_pct_change
from daily
left join daily as week_before
    on daily.activity = week_before.activity
    and week_before.activity_date = cast(daily.activity_date - 7 as date)
