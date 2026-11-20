-- Metric 5: Product Hunt activity per Pacific day. One row per day per activity, with the same
-- weekday a week earlier beside it (a date join, so a missing day cannot shift the pairing).
{%- set release_day = var('producthunt_release_day') %}
with daily as (
    select * from {{ ref('int_producthunt__daily') }}
)

select
    md5(daily.activity || '|' || cast(daily.launch_day as varchar)) as producthunt_day_key,
    daily.launch_day,
    daily.activity,
    case daily.activity
        when 'launches' then 'Launches'
        when 'comments' then 'Comments'
        else daily.activity
    end as activity_label,
    daily.activity_count,
    daily.activity_count is not null as is_available,
    daily.launch_day = date '{{ release_day }}' as is_release_day,
    cast(date_diff('day', date '{{ release_day }}', daily.launch_day) as integer)
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
    and week_before.launch_day = cast(daily.launch_day - 7 as date)
