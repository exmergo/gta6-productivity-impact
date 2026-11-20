-- Metric 4 backup: how far each day's count lands from what the days before it predict.
-- Per activity and candidate day: fit log(count) = a level per weekday + one linear trend on
-- the counted days BEFORE the candidate only, predict the candidate, and measure the gap in
-- prediction standard errors. Release day is one candidate; the earlier ones are placebos.
{%- set release_day = var('github_release_day') %}
{%- set min_fit_days = var('github_test_min_fit_days', 21) %}
with daily as (
    select
        activity,
        activity_date,
        ln(activity_count) as y,
        cast(date_diff('day', date '{{ release_day }}', activity_date) as double) as t,
        isodow(activity_date) as dow
    from {{ ref('fct_github_daily') }}
    where activity_count > 0
        and activity_date <= date '{{ release_day }}'
),

fit as (
    select
        candidate.activity,
        candidate.activity_date as candidate_date,
        history.y,
        history.t,
        history.dow
    from daily as candidate
    inner join daily as history
        on candidate.activity = history.activity
        and history.activity_date < candidate.activity_date
),

weekday_means as (
    select
        activity,
        candidate_date,
        dow,
        avg(t) as mean_t,
        avg(y) as mean_y,
        count(*) as weekday_days
    from fit
    group by activity, candidate_date, dow
),

centered as (
    select
        fit.activity,
        fit.candidate_date,
        fit.t - weekday_means.mean_t as tc,
        fit.y - weekday_means.mean_y as yc
    from fit
    inner join weekday_means
        on fit.activity = weekday_means.activity
        and fit.candidate_date = weekday_means.candidate_date
        and fit.dow = weekday_means.dow
),

trend as (
    select
        activity,
        candidate_date,
        count(*) as fit_days,
        sum(tc * yc) / nullif(sum(tc * tc), 0) as daily_trend,
        sum(tc * tc) as sxx
    from centered
    group by activity, candidate_date
),

weekdays as (
    select activity, candidate_date, count(*) as weekdays
    from weekday_means
    group by activity, candidate_date
),

residuals as (
    select
        centered.activity,
        centered.candidate_date,
        sum(power(centered.yc - trend.daily_trend * centered.tc, 2)) as ssr
    from centered
    inner join trend
        on centered.activity = trend.activity
        and centered.candidate_date = trend.candidate_date
    group by centered.activity, centered.candidate_date
),

scored as (
    select
        daily.activity,
        daily.activity_date as candidate_date,
        trend.fit_days,
        trend.fit_days - weekdays.weekdays - 1 as df,
        trend.daily_trend,
        weekday_means.mean_y + trend.daily_trend * (daily.t - weekday_means.mean_t)
            as expected_log,
        daily.y as observed_log,
        residuals.ssr / nullif(trend.fit_days - weekdays.weekdays - 1, 0) as residual_var,
        1 + 1.0 / weekday_means.weekday_days
            + power(daily.t - weekday_means.mean_t, 2) / nullif(trend.sxx, 0) as variance_factor
    from daily
    inner join trend
        on daily.activity = trend.activity
        and daily.activity_date = trend.candidate_date
    inner join weekdays
        on daily.activity = weekdays.activity
        and daily.activity_date = weekdays.candidate_date
    inner join residuals
        on daily.activity = residuals.activity
        and daily.activity_date = residuals.candidate_date
    inner join weekday_means
        on daily.activity = weekday_means.activity
        and daily.activity_date = weekday_means.candidate_date
        and daily.dow = weekday_means.dow
)

select
    md5(activity || '|' || cast(candidate_date as varchar)) as github_surprise_key,
    activity,
    candidate_date,
    candidate_date = date '{{ release_day }}' as is_release_day,
    fit_days,
    df,
    daily_trend,
    exp(expected_log) as expected_count,
    exp(observed_log) as observed_count,
    100 * (exp(observed_log - expected_log) - 1) as pct_vs_expected,
    case
        when fit_days >= {{ min_fit_days }} and df >= 5 and residual_var > 0
            then (observed_log - expected_log) / sqrt(residual_var * variance_factor)
    end as t_stat
from scored
