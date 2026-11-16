-- The Day-Off Index: geometric mean of per-source lifts (each source the geometric mean of
-- its own component signals), x 100. 100 is a normal week.
with components as (
    select * from {{ ref('fct_thursday_lift') }}
    where is_index_component
),

by_source as (
    select
        study_year,
        source,
        count(*) as signals_total,
        count(lift) as signals_with_lift,
        case
            when count(lift) = count(*) then exp(avg(ln(greatest(lift, 0.01))))
        end as source_lift
    from components
    group by study_year, source
)

select
    study_year,
    case study_year when 2026 then date '2026-11-19' else date '2025-11-20' end as release_day,
    count(*) as sources_total,
    count(source_lift) as sources_with_lift,
    case
        when count(source_lift) = count(*) then 100 * exp(avg(ln(source_lift)))
    end as day_off_index,
    max(case when source = 'google_trends' then source_lift end) as google_trends_lift,
    max(case when source = 'bluesky' then source_lift end) as bluesky_lift,
    max(case when source = 'reddit' then source_lift end) as reddit_lift
from by_source
group by study_year
