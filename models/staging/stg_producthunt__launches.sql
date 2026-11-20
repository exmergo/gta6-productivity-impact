-- One row per Product Hunt launch (Metric 5): its Pacific launch day, and its top-level comments
-- written during that day. Counts and ids only.
select
    post_id,
    cast(day as date) as launch_day,
    launched_at,
    is_featured,
    cast(comments_launch_day as bigint) as comments_launch_day,
    cast(comments_top_level as bigint) as comments_top_level,
    cast(comments_total as bigint) as comments_total,
    observed_at
from {{ source('raw', 'producthunt_launches') }}
