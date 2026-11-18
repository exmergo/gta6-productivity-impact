-- Metric 2, GTA 5 to GTA 6: world productivity in every year from GTA 5's launch year to
-- GTA 6's, and its real change since GTA 5. One row per measure per year.
--   output_per_worker: World Bank GDP per person employed (constant 2021 PPP $).
--   output_per_person: World Bank GDP per capita (constant 2015 US$).
-- A year the World Bank has not published is estimated for output_per_person only: its last
-- published value grown by the IMF's world real GDP growth for each later year, less the
-- World Bank's latest world population growth. output_per_worker stays NULL there
-- (unavailable): no published world employment growth to carry it.
{%- set gta_v = var('gta_v_year', 2013) %}
{%- set gta_6 = var('gta_6_year', 2026) %}
with indicators as (
    select * from {{ ref('stg_economy__indicators') }}
    where geo = 'WLD'
),

measures as (
    select * from (
        values
            ('output_per_worker', 'SL.GDP.PCAP.EM.KD', 'constant 2021 PPP $ per person employed', false),
            ('output_per_person', 'NY.GDP.PCAP.KD', 'constant 2015 US$ per person', true)
    ) as m (measure, source_indicator, unit, carried_by_imf)
),

years as (
    select cast(unnest(range({{ gta_v }}, {{ gta_6 }} + 1)) as integer) as year
),

actuals as (
    select indicator, year, value
    from indicators
    where provider = 'world_bank'
),

last_actual as (
    select indicator, max(year) as last_year, arg_max(value, year) as last_value
    from actuals
    group by indicator
),

gdp_growth as (
    select year, value as gdp_growth_pct
    from indicators
    where provider = 'imf_weo' and indicator = 'NGDP_RPCH'
),

pop_growth as (
    select arg_max(value, year) as pop_growth_pct
    from indicators
    where provider = 'world_bank' and indicator = 'SP.POP.GROW'
),

spine as (
    select
        measures.measure,
        measures.source_indicator,
        measures.unit,
        measures.carried_by_imf,
        years.year,
        actuals.value as actual_value,
        last_actual.last_year,
        last_actual.last_value,
        gdp_growth.gdp_growth_pct,
        pop_growth.pop_growth_pct
    from measures
    cross join years
    cross join pop_growth
    left join actuals
        on actuals.indicator = measures.source_indicator and actuals.year = years.year
    left join last_actual
        on last_actual.indicator = measures.source_indicator
    left join gdp_growth
        on gdp_growth.year = years.year
),

carried as (
    select
        *,
        -- Per-capita growth factor for a year past the last published one; NULL if the IMF
        -- has no growth for it, and a NULL anywhere in the chain keeps the rest NULL.
        case
            when carried_by_imf and year > last_year
                then (1 + gdp_growth_pct / 100) / (1 + pop_growth_pct / 100)
        end as growth_factor
    from spine
),

valued as (
    select
        *,
        case
            when actual_value is not null then actual_value
            when growth_factor is not null and bool_and(growth_factor is not null) over chain
                then last_value * exp(sum(ln(growth_factor)) over chain)
        end as value
    from carried
    window chain as (
        partition by measure, year > last_year
        order by year
        rows between unbounded preceding and current row
    )
),

based as (
    select
        valued.*,
        max(case when year = {{ gta_v }} then value end) over (partition by measure) as gta_v_value,
        max(case when value is not null then year end) over (partition by measure) as latest_year
    from valued
)

select
    md5(measure || '|' || cast(year as varchar)) as world_productivity_key,
    measure,
    year as data_year,
    make_date(year, 1, 1) as year_start,
    case year when {{ gta_v }} then 'GTA 5' when {{ gta_6 }} then 'GTA 6' end as launch,
    value,
    unit,
    source_indicator,
    actual_value is null and value is not null as is_estimate,
    year = latest_year as is_latest,
    round(100 * (value / gta_v_value - 1), 1) as pct_change_since_gta_v
from based
