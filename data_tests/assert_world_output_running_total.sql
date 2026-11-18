-- Metric 3: the last running total is the sum of every day's output, within float rounding,
-- and the running total never falls from one day to the next.
with daily as (
    select
        output_day,
        cumulative_output,
        lag(cumulative_output) over (order by output_day) as previous_output
    from {{ ref('fct_world_output_daily') }}
),

totals as (
    select
        arg_max(cumulative_output, output_day) as last_total,
        (select sum(daily_output) from {{ ref('fct_world_output_daily') }}) as summed
    from daily
)

select 'last total is not the sum of days' as problem, null as output_day
from totals
where last_total is null or abs(last_total - summed) > 1e-6 * summed
union all
select 'running total fell', output_day
from daily
where cumulative_output < previous_output
