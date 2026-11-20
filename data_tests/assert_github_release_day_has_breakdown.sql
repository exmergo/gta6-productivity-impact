-- The GitHub release-day headline never travels without its breakdown.
select *
from {{ ref('fct_github_release_day') }}
where github_release_day_change is not null
    and breakdown is null
