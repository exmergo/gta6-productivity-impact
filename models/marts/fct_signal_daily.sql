select
    md5(
        signals.source || '|' || signals.signal || '|' || signals.geo || '|'
        || cast(signals.signal_date as varchar)
    ) as signal_day_key,
    signals.source,
    signals.signal,
    signals.signal_family,
    signals.geo,
    signals.signal_date,
    signals.signal_value,
    signals.is_available,
    dates.study_year,
    dates.days_from_release,
    dates.iso_day_of_week
from {{ ref('int_signals__daily') }} as signals
inner join {{ ref('dim_date') }} as dates
    on signals.signal_date = dates.date_day
