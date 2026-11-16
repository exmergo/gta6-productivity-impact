-- Each Trends request is scaled to its own 0-100, so we keep exactly one request per
-- (term group, geo, study year): the newest. Mixing requests would mix scales.
with source as (
    select
        *,
        cast(split_part(request_id, '-', 3) as integer) as study_year
    from {{ source('raw', 'trends_interest') }}
),

newest as (
    select term_group, geo, study_year, max(request_id) as request_id
    from source
    group by term_group, geo, study_year
)

select
    source.request_id,
    source.study_year,
    source.term_group,
    source.geo,
    source.term,
    source.day as interest_date,
    cast(source.interest as integer) as interest,
    source.is_partial
from source
inner join newest
    on source.request_id = newest.request_id
