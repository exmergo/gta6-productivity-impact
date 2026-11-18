-- Metric 3, everything humanity made while waiting for GTA 6: one row per UTC day of the
-- wait, from GTA 5's release (var gta_v_date) to the day before GTA 6's (var gta_6_date),
-- with that day's world real output and the running total since GTA 5.
-- Days are generated here: the wait (2013 to 2026) is wider than the semantic time spine.
-- A day whose year has no output reads NULL, and so does every running total from it on.
with days as (
    select cast(range as date) as output_day
    from range(cast('{{ var('gta_v_date', '2013-09-17') }}' as date), cast('{{ var('gta_6_date', '2026-11-19') }}' as date), interval 1 day)
),

yearly as (
    select * from {{ ref('int_world_output__yearly') }}
),

daily as (
    select
        days.output_day,
        cast(year(days.output_day) as integer) as data_year,
        yearly.daily_output,
        yearly.is_estimate
    from days
    left join yearly on yearly.data_year = year(days.output_day)
)

select
    output_day,
    data_year,
    daily_output,
    is_estimate,
    case
        when bool_and(daily_output is not null) over wait
            then sum(daily_output) over wait
    end as cumulative_output,
    datediff('day', cast('{{ var('gta_v_date', '2013-09-17') }}' as date), output_day) + 1 as days_since_gta_v,
    datediff('day', output_day, cast('{{ var('gta_6_date', '2026-11-19') }}' as date)) as days_to_gta_6
from daily
window wait as (order by output_day rows between unbounded preceding and current row)
