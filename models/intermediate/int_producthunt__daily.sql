-- Metric 5: Product Hunt activity per Pacific day, one row per day per activity.
-- launches: the API's count of posts launched that day.
-- comments: top-level comments written on a launch during its launch day, over that day's launches.
-- A day not read in full has comments NULL (unavailable, never zero).
with days as (
    select * from {{ ref('stg_producthunt__days') }}
),

launches as (
    select
        launch_day,
        count(*) as launches_read,
        sum(comments_launch_day) as comments_launch_day
    from {{ ref('stg_producthunt__launches') }}
    group by launch_day
),

activities as (
    select * from (values ('launches', 1), ('comments', 2)) as a (activity, activity_order)
)

select
    days.launch_day,
    activities.activity,
    case activities.activity
        when 'launches' then days.launches_total
        when 'comments' then case
            when days.is_complete and coalesce(launches.launches_read, 0) = days.launches_total
                then coalesce(launches.comments_launch_day, 0)
        end
    end as activity_count,
    days.observed_at
from days
cross join activities
left join launches
    on days.launch_day = launches.launch_day
