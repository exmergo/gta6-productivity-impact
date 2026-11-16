import datetime as dt

import yaml

from gta6_impact.config import ROOT, TRENDS_SPAN, WINDOWS
from gta6_impact.ingest._days import days, epoch

VARS = yaml.safe_load((ROOT / "dbt_project.yml").read_text())["vars"]


def _windows() -> tuple[tuple[dt.date, dt.date], tuple[dt.date, dt.date]]:
    start = dt.date.fromisoformat(VARS["day_off_index_start_week"])
    end_var = VARS.get("day_off_index_end_week")
    end = (
        dt.date.fromisoformat(end_var)
        if end_var
        else start + dt.timedelta(weeks=VARS["day_off_index_weeks"] - 1)
    )
    back = dt.timedelta(weeks=VARS["day_off_index_weeks_back"])
    return (start, end), (start - back, end - back)


def test_index_weeks_are_google_weeks():
    # Google's weekly Trends rows are labelled by their Sunday.
    for first, last in _windows():
        assert first.weekday() == 6 and last.weekday() == 6
        assert first <= last


def test_trends_span_covers_both_index_windows():
    (current, prior) = _windows()
    span_start, span_end = TRENDS_SPAN
    assert span_start.isoformat() == VARS["day_off_index_span_start"]
    assert span_end.isoformat() == VARS["day_off_index_span_end"]
    # The first Google week inside the span starts on or after span_start.
    assert span_start <= prior[0]
    assert current[1] + dt.timedelta(days=6) <= span_end


def test_canonical_window_is_the_published_one():
    assert _windows() == (
        (dt.date(2026, 11, 1), dt.date(2026, 11, 8)),
        (dt.date(2025, 11, 2), dt.date(2025, 11, 9)),
    )


def test_control_window_aligns_weekdays():
    assert WINDOWS[0].start.weekday() == WINDOWS[1].start.weekday()


def test_days_and_epoch():
    window = WINDOWS[0]
    assert len(list(days(window, until=window.start + dt.timedelta(days=2)))) == 3
    assert epoch(dt.date(1970, 1, 2)) == 86400
