-- int_signals__daily: the natural grain behind the surrogate key is unique.
select source, signal, geo, signal_date, count(*) as rows_per_key
from {{ ref('int_signals__daily') }}
group by source, signal, geo, signal_date
having count(*) > 1
