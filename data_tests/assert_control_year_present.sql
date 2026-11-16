-- Every index component signal of the study year has its 2025 control.
select study.source, study.signal, study.geo
from {{ ref('fct_thursday_lift') }} as study
left join {{ ref('fct_thursday_lift') }} as control
    on study.source = control.source
    and study.signal = control.signal
    and study.geo = control.geo
    and control.study_year = 2025
where study.study_year = 2026
  and study.signal_family = 'day_off_intent'
  and study.source in ('google_trends', 'bluesky', 'reddit')
  and control.signal is null
