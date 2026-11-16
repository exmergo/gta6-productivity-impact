import datetime as dt

from gta6_impact.config import (
    BASELINE_DAY,
    CONTROL_BASELINE_DAY,
    CONTROL_RELEASE_DAY,
    RELEASE_DAY,
    WINDOWS,
)
from gta6_impact.ingest._days import days, epoch

PAIRS = ((RELEASE_DAY, BASELINE_DAY), (CONTROL_RELEASE_DAY, CONTROL_BASELINE_DAY))


def test_comparison_days_are_thursdays_one_week_apart():
    for release, baseline in PAIRS:
        assert release.weekday() == 3 and baseline.weekday() == 3
        assert release - baseline == dt.timedelta(days=7)


def test_windows_contain_both_thursdays():
    for window, pair in zip(WINDOWS, PAIRS, strict=True):
        for day in pair:
            assert window.start <= day <= window.end


def test_control_window_aligns_weekdays():
    assert WINDOWS[0].start.weekday() == WINDOWS[1].start.weekday()


def test_days_and_epoch():
    window = WINDOWS[0]
    assert len(list(days(window, until=window.start + dt.timedelta(days=2)))) == 3
    assert epoch(dt.date(1970, 1, 2)) == 86400
