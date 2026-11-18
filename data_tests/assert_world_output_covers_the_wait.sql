-- Metric 3: the wait holds every UTC day from GTA V's release to the day before GTA 6's,
-- once each (4,811 days for 2013-09-17 to 2026-11-18).
select count(*) as days, min(output_day) as first_day, max(output_day) as last_day
from {{ ref('fct_world_output_daily') }}
having count(*) <> datediff('day', cast('{{ var('gta_v_date', '2013-09-17') }}' as date), cast('{{ var('gta_6_date', '2026-11-19') }}' as date))
    or min(output_day) <> cast('{{ var('gta_v_date', '2013-09-17') }}' as date)
    or max(output_day) <> cast('{{ var('gta_6_date', '2026-11-19') }}' as date) - 1
