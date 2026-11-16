-- The Day-Off Index breakdown: one row per search phrase, its average weekly search
-- interest over the current window and over the same weeks a year earlier, and the change.
-- The window is configurable (vars day_off_index_*): a start week and an end week, or a
-- start week and a number of weeks. Weeks are Google's, labelled by their Sunday.
{%- set start_week = var('day_off_index_start_week') %}
{%- set end_week = var('day_off_index_end_week', none) %}
{%- set weeks = var('day_off_index_weeks', 2) %}
{%- set weeks_back = var('day_off_index_weeks_back', 52) %}
with params as (
    select
        date '{{ start_week }}' as current_start_week,
        {% if end_week -%}
        date '{{ end_week }}'
        {%- else -%}
        cast(date '{{ start_week }}' + 7 * ({{ weeks }} - 1) as date)
        {%- endif %} as current_end_week
),

windows as (
    select
        current_start_week,
        current_end_week,
        cast(current_start_week - 7 * {{ weeks_back }} as date) as prior_start_week,
        cast(current_end_week - 7 * {{ weeks_back }} as date) as prior_end_week,
        cast((current_end_week - current_start_week) / 7 + 1 as integer) as weeks
    from params
),

phrases as (
    select distinct term, geo, batch_id, span_start, span_end
    from {{ ref('stg_trends__weekly') }}
),

per_phrase as (
    select
        phrases.term,
        phrases.geo,
        phrases.batch_id,
        phrases.span_start,
        phrases.span_end,
        windows.current_start_week,
        windows.current_end_week,
        windows.prior_start_week,
        windows.prior_end_week,
        windows.weeks,
        avg(weekly.interest) filter (
            where weekly.week_start between windows.current_start_week
                and windows.current_end_week and not weekly.is_partial
        ) as current_avg_interest,
        avg(weekly.interest) filter (
            where weekly.week_start between windows.prior_start_week
                and windows.prior_end_week and not weekly.is_partial
        ) as prior_avg_interest,
        count(weekly.week_start) filter (
            where weekly.week_start between windows.current_start_week
                and windows.current_end_week and not weekly.is_partial
        ) as current_weeks_found,
        count(weekly.week_start) filter (
            where weekly.week_start between windows.prior_start_week
                and windows.prior_end_week and not weekly.is_partial
        ) as prior_weeks_found
    from phrases
    cross join windows
    left join {{ ref('stg_trends__weekly') }} as weekly
        on phrases.term = weekly.term
    group by
        phrases.term,
        phrases.geo,
        phrases.batch_id,
        phrases.span_start,
        phrases.span_end,
        windows.current_start_week,
        windows.current_end_week,
        windows.prior_start_week,
        windows.prior_end_week,
        windows.weeks
)

select
    term,
    geo,
    batch_id,
    span_start,
    span_end,
    current_start_week,
    current_end_week,
    prior_start_week,
    prior_end_week,
    weeks,
    current_weeks_found,
    prior_weeks_found,
    current_avg_interest,
    prior_avg_interest,
    case
        when current_weeks_found = weeks
            and prior_weeks_found = weeks
            and prior_avg_interest > 0
            then 100 * (current_avg_interest / prior_avg_interest - 1)
    end as pct_change
from per_phrase
