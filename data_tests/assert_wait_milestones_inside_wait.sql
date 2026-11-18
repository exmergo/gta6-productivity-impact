-- Metric 3: every milestone other than GTA 5's release falls inside the wait, so its output
-- by then (the day before) exists: from the day after GTA 5's release to GTA 6's release day.
select milestone_id, event_date, output_by_then
from {{ ref('fct_wait_milestones') }}
where event_date <> cast('{{ var('gta_v_date', '2013-09-17') }}' as date)
  and (
    event_date <= cast('{{ var('gta_v_date', '2013-09-17') }}' as date)
    or event_date > cast('{{ var('gta_6_date', '2026-11-19') }}' as date)
    or output_by_then is null
  )
