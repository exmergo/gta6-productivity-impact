# The Dex audit trail

Raw command envelopes, in the order they ran. The payloads they were planned from are in
`../payloads/`, and the plans in `../plans/`.

| Step | Evidence | What it shows |
|---|---|---|
| 01 | `01-map.json` | `dex explore map`: the raw tables Dex found, their grain and PII flags |
| 02 | `02-profile-trends-wiki.json` | Profile of Trends and Wikipedia. Finds Wikipedia timestamps rendered at +01:00/+02:00 in a local session, so staging converts to UTC explicitly |
| 03–04 | `03-profile-bluesky.json`, `04-profile-hn.json` | Profiles of the daily-hit tables. Dex's drafted grain (`observed_at`) is trivially unique; the real grain is proven in 05–06 |
| 05 | `05-query-hn-volume-and-grain.json` | Hacker News: 334 day-off hits in 107 days. Too sparse for the index |
| 06–07 | `06-query-bluesky-grain.json`, `07-query-trends-grain.json` | Exact grain probes behind the staging declarations |
| 08–10 | `08-plan-staging.json` → `10-build-staging.json` | Staging plan with declarations, applied, built and verified: `validated`, 19 tests |
| 11–13 | `11-plan-marts.json` → `13-build-marts.json` | Intermediate and marts. The population guard refused the first apply until a request-tier assumption recorded why days outside the study window are dropped. `validated`, 64 tests. `11` also carries the drafted `semantic_proposal` |
| 14–16 | `14-plan-time-spine.json` → `16-build-time-spine.json` | MetricFlow time spine |
| 17–19 | `17-semantic-define.json` → `19-semantic-list.json` | Semantic models (from the proposal) and 12 metrics, applied and listed |
| 20 | `20-config-max-rows.json` | Raising `query.max_rows` from 50 so charts get whole series (a reviewable config diff, confirmed) |
| 21 | `21-profile-marts.json` | Profiles of the built marts, for evidence-backed PII screening |
| 22 | `22-maintain-verify.json` | Every declared grain proven (10 of 10) |
| 23 | `23-maintain-snapshot.json` | The committed baseline in `../snapshot.json` |
| 24–26 | `24-semantic-define-gta-posts.json` → `26-build-gta-posts.json` | A first headline metric (Bluesky day-off posts mentioning GTA, YoY): defined, applied, `validated` |
| 27–29 | `27-semantic-plan-day-off-yoy.json` → `29-build-day-off-yoy.json` | Replaced by generic Bluesky day-off posts YoY: planned, applied, `validated` |
| 30–34 | `30-plan-trends-single-term.json` → `34-build-trends.json` | Google Trends reworked: one phrase per request, US only. `32` is the comparison Dex ran before applying: `unexpected` (2,260 rows to 1,396, against the stated expectation). The build in `34` is `built_unverified`: the comparison for `stg_trends__interest` was not run |
| 35–38 | `35-plan-day-off-index.json` → `38-build-day-off-index.json` | The Day-Off Index redefined as a YoY comparison of US Google searches. Planned twice, applied, and built `built_unverified` (comparisons not run for `dim_date`, `fct_day_off_index`, `fct_signal_daily`) |
| 39 | `39-scaffold-terms.json` | `dex transform test --scaffold` refused `fct_day_off_index_terms`: the model's jinja `set` block can't be scaffolded, so the unit tests were written by hand and planned in `40` |
| 40–43 | `40-plan-unit-tests.json` → `43-build-full.json` | Unit tests for the window settings, partial weeks, the average and the breakdown, then a full build: `validated` |
| 44–52 | `44-maintain-verify.json` → `52-maintain-check.json` | Verify, snapshot and drift checks around the new index, including a re-map (`47`) and profiles of the changed tables (`50`) |
| 53–55 | `53-plan-remove-reddit.json` → `55-build-remove-reddit.json` | Removing the unused Reddit sources: planned, applied, `validated` |
| 56–58 | `56-maintain-check.json` → `58-maintain-check.json` | The drift baseline refreshed for the new index, then checked against it |
| refresh/ | `refresh/*.json` | The latest scheduled run: build, map and `maintain check` |
| 235–241 | `235-plan-producthunt.json` → `241-query-producthunt-release-day.json` | Metric 5 (Product Hunt on release day): raw profiled, staging, intermediate and marts planned with declarations, applied, built `validated`. The one introduced finding (`row_fanout` on `int_producthunt__daily`) is its declared grain, one row per day per activity |
| 242–247 | `242-plan-producthunt-semantic.json` → `247-semantic-list-producthunt.json` | Metric 5 semantic models and 8 metrics, applied, rebuilt with 12 Nov loaded (`validated`) and listed. The high `population_delta` on `fct_github_release_day_activities` compares it with a parent Dex drafted from the new Product Hunt mart (shared `activity` key); no GitHub row moved |
| 248–250 | `248-semantic-query-producthunt-headline.json` → `250-query-producthunt-comment-split.json` | The headline (launches +1.9%, comments +57.2%), its breakdown, and the comment split behind it (featured vs not, launches with comments) |
| 251–252 | `251-build-producthunt-18nov.json`, `252-semantic-query-producthunt-daily.json` | 18 Nov (the day before) loaded as context: rebuilt `validated`, daily counts |
