select
    day as hit_date,
    seed,
    gta_filter,
    query,
    cast(hits_total as bigint) as hits_total,
    hits_total is not null as is_available,
    observed_at
from {{ source('raw', 'bluesky_daily_hits') }}
