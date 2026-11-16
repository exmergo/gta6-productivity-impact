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
| refresh/ | `refresh/*.json` | The latest scheduled run: build, map and `maintain check` |
