-- The Day-Off Index never travels without its breakdown: a row with an index has one.
select *
from {{ ref('fct_day_off_index') }}
where day_off_index is not null
    and (breakdown is null or phrases_available <> phrase_count)
