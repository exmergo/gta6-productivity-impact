import pytest

from gta6_impact.stats import t_lower_tail


@pytest.mark.parametrize(
    ("t", "df", "p"),
    [
        (-2.0, 10, 0.036694),  # textbook table values
        (-1.812461, 10, 0.05),
        (-2.763769, 10, 0.01),
        (-1.683851, 40, 0.05),
        (-2.570582, 5, 0.025),
        (0.0, 7, 0.5),
    ],
)
def test_t_lower_tail_matches_tables(t, df, p):
    assert t_lower_tail(t, df) == pytest.approx(p, abs=2e-6)


def test_t_lower_tail_is_symmetric():
    assert t_lower_tail(1.5, 12) == pytest.approx(1 - t_lower_tail(-1.5, 12), abs=1e-12)
