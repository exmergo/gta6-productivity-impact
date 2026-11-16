# How we measure a vibe

GTA 6 comes out on Thursday 19 November 2026. Nobody publishes how many people booked
that day off. So we measure what people *say* and *search*, and compare it with the
Thursday before.

## The comparison

Every number in this repo is a **Thursday lift**:

```
lift = value on Thu 19 Nov 2026 / value on Thu 12 Nov 2026
```

A lift of 1.00 means a normal week. People also take more time off as Thanksgiving gets
closer, so every lift has a **seasonality control**: the same ratio one year earlier, Thu
20 Nov 2025 against Thu 13 Nov 2025. GTA 6 wasn't out then. The part of the lift we put
down to GTA is the gap between the two.

## The Day-Off Index

The **Day-Off Index** is the geometric mean of the Thursday lifts of the intent signals,
× 100. It is 100 in a normal week.

| Signal | Source | What it counts |
|---|---|---|
| Search intent | Google Trends, US + worldwide | Relative daily interest in "call in sick", "sick day", "PTO", "day off work" |
| Bluesky day-off posts | Bluesky public search, `hitsTotal` | Posts per UTC day matching each day-off phrase |
| Reddit day-off items | Arctic Shift archive | Posts and comments per UTC day matching a day-off phrase, in 9 subreddits |

Supporting numbers, kept out of the index:

- **GTA share of day-off talk**: day-off posts that also say GTA, as a share of all
  day-off posts. "People post more on Thursdays" affects both the top and the bottom of
  this ratio, so it cancels out.
- **Hype**: Wikipedia daily views of *Grand Theft Auto VI*, and Google Trends interest in
  "GTA 6".
- **Hacker News**: the same phrases on HN. There are very few matches, so it's here for
  the joke.

## Integrity rules

1. **Every day is a UTC day.** A local Thursday in Sydney and one in San Francisco are
   different UTC slices, and we say which slice we use.
2. **Missing is unavailable, never zero.** A failed pull leaves a gap. It doesn't put a 0
   in a lift.
3. **Trends values only compare within one request.** Google rescales every request to
   0–100, so both Thursdays of a year always come from the same request, and each pull
   keeps its `request_id`.
4. **Half a day isn't a day.** We only count UTC days that are over.
5. **No people, only counts.** We store no post text, handles, usernames or URIs. Reddit
   items keep an id, a timestamp and two booleans worked out in memory.
6. **Association only.** A lift says Thursday was different. It doesn't prove GTA caused
   it, although the control year and the GTA share help.

## Two honest limits

- This is a public-signal proxy, not a headcount. People who quietly book PTO in an HR
  system don't post about it. The closest outside figure we know of is BambooHR's
  reported +9–17% in time-off requests for 19 Nov. That's an outside reference, not our
  data.
- Search indexes change. Bluesky's `hitsTotal` and Algolia's `nbHits` are what those
  services report, and `dex maintain check` watches every refresh for sudden volume
  drift.
