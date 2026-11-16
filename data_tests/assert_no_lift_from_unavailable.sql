-- A lift is only computed when both Thursdays were actually read.
select *
from {{ ref('fct_thursday_lift') }}
where lift is not null
  and not (is_baseline_available and is_release_available)
