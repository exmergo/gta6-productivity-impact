-- Metric 3, everything humanity made while waiting for GTA 6: world real output in every
-- year from GTA 5's launch year to GTA 6's. One row per year.
-- World Bank WDI GDP (NY.GDP.MKTP.KD, constant 2015 US$, world aggregate). A year the World
-- Bank has not published is its last published value grown by the IMF WEO world real GDP
-- growth for each later year (total output: no population adjustment), flagged is_estimate.
-- A missing IMF year leaves that year and every later one NULL: unavailable, never zero.
with indicators as (
    select * from {{ ref('stg_economy__indicators') }}
    where geo = 'WLD'
),

years as (
    select cast(unnest(range({{ var('gta_v_year', 2013) }}, {{ var('gta_6_year', 2026) }} + 1)) as integer) as year
),

actuals as (
    select year, value
    from indicators
    where provider = 'world_bank' and indicator = 'NY.GDP.MKTP.KD'
),

last_actual as (
    select max(year) as last_year, arg_max(value, year) as last_value
    from actuals
),

gdp_growth as (
    select year, value as gdp_growth_pct
    from indicators
    where provider = 'imf_weo' and indicator = 'NGDP_RPCH'
),

spine as (
    select
        years.year,
        actuals.value as actual_value,
        last_actual.last_year,
        last_actual.last_value,
        gdp_growth.gdp_growth_pct
    from years
    left join last_actual on true
    left join actuals on actuals.year = years.year
    left join gdp_growth on gdp_growth.year = years.year
),

carried as (
    select
        *,
        case when year > last_year then 1 + gdp_growth_pct / 100 end as growth_factor
    from spine
),

valued as (
    select
        *,
        case
            when actual_value is not null then actual_value
            when growth_factor is not null and bool_and(growth_factor is not null) over chain
                then last_value * exp(sum(ln(growth_factor)) over chain)
        end as annual_output
    from carried
    window chain as (
        partition by year > last_year
        order by year
        rows between unbounded preceding and current row
    )
),

sized as (
    select
        *,
        datediff('day', make_date(year, 1, 1), make_date(year + 1, 1, 1)) as days_in_year
    from valued
)

select
    year as data_year,
    annual_output,
    actual_value is null and annual_output is not null as is_estimate,
    days_in_year,
    annual_output / days_in_year as daily_output,
    annual_output / days_in_year / 86400 as output_per_second,
    'NY.GDP.MKTP.KD' as source_indicator
from sized
