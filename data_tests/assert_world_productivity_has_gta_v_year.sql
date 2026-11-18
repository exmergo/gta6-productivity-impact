-- Metric 2 is measured from GTA 5's launch year: every measure needs its bookend value, or
-- every change since GTA 5 would read NULL.
select measure
from {{ ref('fct_world_productivity') }}
group by measure
having max(case when data_year = {{ var('gta_v_year', 2013) }} then value end) is null
