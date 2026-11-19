-- The GitHub release-day change never travels without its breakdown.
select *
from {{ ref('fct_github_release_day') }}
where github_release_day_change is not null
    and (breakdown is null or activities_available <> activities_total)
