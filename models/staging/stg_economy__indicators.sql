-- One row per provider, indicator, geography and year of official economic data.
with source as (
    select * from {{ source('raw', 'economy_indicators') }}
)

select
    provider,
    indicator,
    geo,
    cast(year as integer) as year,
    cast(value as double) as value,
    cast(last_updated as date) as last_updated
from source
