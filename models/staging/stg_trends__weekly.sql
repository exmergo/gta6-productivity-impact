-- One row per search phrase per Google week (labelled by its Sunday), from one weekly
-- Trends request per phrase that spans both years, so 2025 and 2026 share one 0-100 scale.
-- Keeps the requests over the configured span (older daily per-year pulls have no span and
-- drop out), and the pinned batch (var day_off_index_batch) or else the newest per phrase.
{%- set batch = var('day_off_index_batch', none) %}
with source as (
    select *
    from {{ source('raw', 'trends_interest') }}
    where span_start = date '{{ var("day_off_index_span_start") }}'
        and span_end = date '{{ var("day_off_index_span_end") }}'
),

chosen as (
    select
        term,
        {% if batch %}'{{ batch }}'{% else %}max(batch_id){% endif %} as batch_id
    from source
    group by term
)

select
    source.request_id,
    source.batch_id,
    source.span_start,
    source.span_end,
    source.geo,
    source.term,
    source.day as week_start,
    cast(source.interest as integer) as interest,
    source.is_partial
from source
inner join chosen
    on source.term = chosen.term
    and source.batch_id = chosen.batch_id
