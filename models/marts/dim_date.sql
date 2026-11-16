-- One row per UTC day of the study window and its control year, with its place relative
-- to that year's release Thursday.
with spine as (
    select cast(range as date) as date_day
    from range(date '2025-10-01', date '2027-01-01', interval 1 day)
),

years as (
    select
        date_day,
        case when date_day >= date '2026-01-01' then 2026 else 2025 end as study_year
    from spine
),

anchored as (
    select
        date_day,
        study_year,
        case study_year when 2026 then date '2026-11-19' else date '2025-11-20' end as release_day
    from years
)

select
    date_day,
    study_year,
    release_day,
    cast(date_day - release_day as integer) as days_from_release,
    isodow(date_day) as iso_day_of_week,
    dayname(date_day) as day_name,
    case cast(date_day - release_day as integer)
        when 0 then 'release'
        when -7 then 'baseline'
    end as comparison_role,
    study_year = 2026 and date_day = release_day as is_gta_release_day
from anchored
