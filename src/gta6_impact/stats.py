"""Student t probabilities, without scipy: the one-sided p-value of a t-test.

The test statistic and its degrees of freedom come from the semantic layer
(`github_release_day_t`, `github_release_day_df`); this only reads the tail probability.
"""

from __future__ import annotations

import math


def _beta_cf(a: float, b: float, x: float) -> float:
    """Continued fraction for the regularized incomplete beta (Lentz's method)."""
    tiny, eps = 1e-300, 1e-15
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 500):
        for num in (
            m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)),
            -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1)),
        ):
            d = 1.0 + num * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + num / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_cf(a, b, x) / a
    return 1.0 - front * _beta_cf(b, a, 1.0 - x) / b


def t_lower_tail(t: float, df: float) -> float:
    """P(T <= t) for Student's t with df degrees of freedom: the one-sided p of a drop."""
    tail = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return tail if t <= 0 else 1.0 - tail
