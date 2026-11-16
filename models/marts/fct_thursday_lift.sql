-- Release Thursday over the Thursday before, per signal and study year.
with pairs as (
    select
        source,
        signal,
        signal_family,
        geo,
        study_year,
        max(signal_value) filter (where comparison_role = 'baseline') as baseline_value,
        max(signal_value) filter (where comparison_role = 'release') as release_value,
        coalesce(bool_or(is_available) filter (where comparison_role = 'baseline'), false)
            as is_baseline_available,
        coalesce(bool_or(is_available) filter (where comparison_role = 'release'), false)
            as is_release_available
    from {{ ref('fct_signal_daily') }}
    where comparison_role is not null
    group by source, signal, signal_family, geo, study_year
)

select
    md5(source || '|' || signal || '|' || geo || '|' || cast(study_year as varchar))
        as thursday_lift_key,
    source,
    signal,
    signal_family,
    geo,
    study_year,
    case study_year when 2026 then date '2026-11-19' else date '2025-11-20' end as release_day,
    baseline_value,
    release_value,
    is_baseline_available,
    is_release_available,
    case
        when is_baseline_available and is_release_available and baseline_value > 0
            then release_value / baseline_value
    end as lift,
    signal_family = 'day_off_intent'
    and source in ('google_trends', 'bluesky', 'reddit')
    and (source <> 'google_trends' or baseline_value >= 5) as is_index_component
from pairs
