-- One row per Pacific day Product Hunt was asked about (Metric 5). launches_total is the API's
-- own count of posts launched that day; is_complete says every one of them was listed and read.
select
    cast(day as date) as launch_day,
    day_start,
    day_end,
    cast(launches_total as bigint) as launches_total,
    cast(launches_listed as bigint) as launches_listed,
    coalesce(launches_listed = launches_total, false) as is_complete,
    observed_at
from {{ source('raw', 'producthunt_days') }}
