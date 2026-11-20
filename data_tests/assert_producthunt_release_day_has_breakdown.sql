-- The Product Hunt release-day changes never travel without their breakdown.
select *
from {{ ref('fct_producthunt_release_day') }}
where (producthunt_launches_change is not null or producthunt_comments_change is not null)
    and breakdown is null
