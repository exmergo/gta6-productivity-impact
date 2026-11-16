-- Every signal as one daily value per (source, signal, geo, UTC day).
-- A value that could not be read is NULL with is_available = false: unavailable, never zero.
with bluesky as (
    select
        'bluesky' as source,
        case gta_filter when 'gta' then 'posts:day_off_gta' else 'posts:day_off' end as signal,
        case gta_filter when 'gta' then 'day_off_gta' else 'day_off_intent' end as signal_family,
        'WORLD' as geo,
        hit_date as signal_date,
        case when bool_and(is_available) then cast(sum(hits_total) as double) end as signal_value,
        bool_and(is_available) as is_available
    from {{ ref('stg_bluesky__daily_hits') }}
    group by gta_filter, hit_date
),

hacker_news as (
    select
        'hacker_news' as source,
        case gta_filter when 'gta' then 'posts:day_off_gta' else 'posts:day_off' end as signal,
        case gta_filter when 'gta' then 'day_off_gta' else 'day_off_intent' end as signal_family,
        'WORLD' as geo,
        hit_date as signal_date,
        case when bool_and(is_available) then cast(sum(hits_total) as double) end as signal_value,
        bool_and(is_available) as is_available
    from {{ ref('stg_hn__daily_hits') }}
    group by gta_filter, hit_date
),

wikipedia as (
    select
        'wikipedia' as source,
        'pageviews:' || lower(article) as signal,
        case when article = 'Grand_Theft_Auto_VI' then 'hype' else 'reference' end as signal_family,
        'WORLD' as geo,
        view_date as signal_date,
        cast(views as double) as signal_value,
        true as is_available
    from {{ ref('stg_wiki__pageviews') }}
)

select * from bluesky
union all
select * from hacker_news
union all
select * from wikipedia
