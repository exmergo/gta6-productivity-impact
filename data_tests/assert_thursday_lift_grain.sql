-- fct_thursday_lift: the natural grain behind the surrogate key is unique.
select source, signal, geo, study_year, count(*) as rows_per_key
from {{ ref('fct_thursday_lift') }}
group by source, signal, geo, study_year
having count(*) > 1
