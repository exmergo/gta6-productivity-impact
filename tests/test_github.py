import datetime as dt

import yaml

from gta6_impact.config import GITHUB_ACTIVITIES, GITHUB_SPAN, RELEASE_DAY, ROOT
from gta6_impact.ingest.github import query

VARS = yaml.safe_load((ROOT / "dbt_project.yml").read_text())["vars"]


def test_each_query_covers_exactly_one_utc_day():
    day = dt.date(2026, 11, 19)
    for activity in GITHUB_ACTIVITIES:
        _, q = query(activity, day)
        assert "2026-11-19T00:00:00Z..2026-11-19T23:59:59Z" in q
        assert "2026-11-18" not in q and "2026-11-20" not in q


def test_prs_are_pull_requests_not_issues():
    assert query("prs_opened", RELEASE_DAY)[1].startswith("is:pr created:")
    assert query("prs_merged", RELEASE_DAY)[1].startswith("is:pr is:merged merged:")
    assert query("commits", RELEASE_DAY)[0] == "commits"


def test_release_day_var_is_gta_6_day():
    assert dt.date.fromisoformat(VARS["github_release_day"]) == RELEASE_DAY
    assert RELEASE_DAY.weekday() == 3  # Thursday


def test_span_covers_the_baseline_and_two_weeks_after():
    release = dt.date.fromisoformat(VARS["github_release_day"])
    first_baseline = release - dt.timedelta(weeks=VARS["github_baseline_weeks"])
    assert GITHUB_SPAN[0] <= first_baseline
    assert GITHUB_SPAN[1] >= release + dt.timedelta(days=14)
