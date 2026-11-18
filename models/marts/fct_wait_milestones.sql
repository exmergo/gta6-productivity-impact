-- Metric 3: each milestone of the wait, placed on the running total of world real output.
-- output_by_then is the running total through the day before the event: "by the time it
-- happened, the world had made $X since GTA V". GTA V's own release day has made nothing yet
-- since GTA V, so it reads 0; any other milestone outside the wait reads NULL.
with milestones as (
    select * from {{ ref('wait_milestones') }}
),

daily as (
    select * from {{ ref('fct_world_output_daily') }}
),

wait as (
    select arg_max(cumulative_output, output_day) as wait_output
    from daily
)

select
    milestones.milestone_id,
    milestones.event_date,
    milestones.date_precision,
    milestones.category,
    milestones.tier,
    milestones.is_editorial,
    milestones.title,
    milestones.chart_label,
    milestones.why,
    milestones.source_url,
    case
        when milestones.event_date = cast('{{ var('gta_v_date', '2013-09-17') }}' as date) then 0
        else daily.cumulative_output
    end as output_by_then,
    output_by_then / wait.wait_output as share_of_wait_output,
    datediff('day', cast('{{ var('gta_v_date', '2013-09-17') }}' as date), milestones.event_date) as days_since_gta_v,
    datediff('day', milestones.event_date, cast('{{ var('gta_6_date', '2026-11-19') }}' as date)) as days_to_gta_6
from milestones
left join wait on true
left join daily on daily.output_day = milestones.event_date - 1
