-- Metric 4 backup: the release-day test, one row per activity. The primary test (release
-- day against the weekday-and-trend prediction from the days before it), its placebo rank
-- among the earlier days, and the Thursday check (release day's week-on-week change against
-- the earlier same-weekday changes). p-values are read from t and df downstream.
{%- set release_day = var('github_release_day') %}
with surprise as (
    select * from {{ ref('fct_github_day_surprise') }}
),

release as (
    select * from surprise where is_release_day
),

placebos as (
    select
        release.activity,
        count(surprise.t_stat) as placebo_days,
        count(surprise.t_stat) filter (where surprise.t_stat <= release.t_stat)
            as placebo_days_as_low
    from release
    left join surprise
        on release.activity = surprise.activity
        and surprise.candidate_date < release.candidate_date
    group by release.activity
),

weekday as (
    select
        activity,
        count(wow_pct_change) filter (where not is_release_day) as weekday_n,
        avg(wow_pct_change) filter (where not is_release_day) as weekday_wow_mean,
        stddev_samp(wow_pct_change) filter (where not is_release_day) as weekday_wow_sd,
        max(wow_pct_change) filter (where is_release_day) as release_wow
    from {{ ref('fct_github_daily') }}
    where dayofweek(activity_date) = dayofweek(date '{{ release_day }}')
        and activity_date <= date '{{ release_day }}'
    group by activity
)

select
    release.activity,
    release.candidate_date as release_day,
    release.fit_days,
    release.df,
    release.expected_count,
    release.observed_count,
    release.pct_vs_expected,
    release.t_stat,
    placebos.placebo_days,
    placebos.placebo_days_as_low,
    case
        when release.t_stat is not null and placebos.placebo_days > 0
            then (placebos.placebo_days_as_low + 1.0) / (placebos.placebo_days + 1)
    end as placebo_p,
    weekday.weekday_n,
    weekday.weekday_wow_mean,
    weekday.weekday_wow_sd,
    weekday.release_wow,
    case
        when weekday.weekday_n >= 3 and weekday.weekday_wow_sd > 0
            then (weekday.release_wow - weekday.weekday_wow_mean)
                / (weekday.weekday_wow_sd * sqrt(1 + 1.0 / weekday.weekday_n))
    end as weekday_t,
    weekday.weekday_n - 1 as weekday_df
from release
inner join placebos
    on release.activity = placebos.activity
left join weekday
    on release.activity = weekday.activity
