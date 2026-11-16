with source as (
    select * from {{ source('raw', 'wiki_pageviews') }}
)

select
    article,
    cast(timezone('UTC', ts) as date) as view_date,
    cast(views as bigint) as views
from source
where granularity = 'daily'
