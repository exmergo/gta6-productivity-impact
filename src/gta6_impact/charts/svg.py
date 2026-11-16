"""Hand-drawn SVG marks in the trydex.ai drawing style: thin lines, labels in the DOM,
colours from brand tokens only (CSS classes, never hex)."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape


@dataclass
class Series:
    label: str
    points: list[tuple[float, float | None]]
    css: str = "s-study"  # s-study (blue), s-control (faint ink)
    fmt: str = "{:.0f}"
    point_titles: list[str] = field(default_factory=list)


def _nice_max(value: float) -> float:
    if value <= 0:
        return 1.0
    import math

    exp = 10 ** math.floor(math.log10(value))
    for step in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if step * exp >= value:
            return step * exp
    return 10 * exp


def line_chart(
    series: list[Series],
    *,
    width: int,
    height: int,
    x_min: float,
    x_max: float,
    y_fmt: str = "{:.0f}",
    x_label=lambda x: f"{int(x):+d}" if x else "0",
    x_ticks: list[float] | None = None,
    marker_x: float | None = 0,
    marker_label: str = "Release",
    y_max: float | None = None,
    notes: list[tuple[float, float, str]] | None = None,
) -> str:
    pad_l, pad_r, pad_t, pad_b = 70, 150, 24, 44
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    values = [y for s in series for _, y in s.points if y is not None]
    top = y_max or _nice_max(max(values) if values else 1)

    def sx(x: float) -> float:
        return pad_l + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return pad_t + plot_h - (y / top) * plot_h

    out = [
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" '
        f'role="img" class="chart">'
    ]
    for i in range(5):
        y = top * i / 4
        out.append(
            f'<line class="grid" x1="{pad_l}" x2="{pad_l + plot_w}" '
            f'y1="{sy(y):.1f}" y2="{sy(y):.1f}"/>'
        )
        out.append(
            f'<text class="tick" x="{pad_l - 12}" y="{sy(y) + 5:.1f}" '
            f'text-anchor="end">{escape(y_fmt.format(y))}</text>'
        )
    for x in x_ticks or []:
        out.append(
            f'<text class="tick" x="{sx(x):.1f}" y="{height - 14}" '
            f'text-anchor="middle">{escape(x_label(x))}</text>'
        )
    if marker_x is not None and x_min <= marker_x <= x_max:
        mx = sx(marker_x)
        out.append(
            f'<line class="marker" x1="{mx:.1f}" x2="{mx:.1f}" y1="{pad_t - 6}" '
            f'y2="{pad_t + plot_h}"/>'
        )
        out.append(
            f'<text class="marker-label" x="{mx + 8:.1f}" y="{pad_t + 6}">'
            f"{escape(marker_label)}</text>"
        )
    label_slots: list[float] = []
    for s in series:
        pts = [(x, y) for x, y in s.points if y is not None and x_min <= x <= x_max]
        if not pts:
            continue
        path, pen = [], "M"
        prev_x = None
        for x, y in sorted(pts):
            if prev_x is not None and x - prev_x > 1:
                pen = "M"  # gap: unavailable days are not drawn as zeros
            path.append(f"{pen}{sx(x):.1f},{sy(y):.1f}")
            pen, prev_x = "L", x
        out.append(f'<path class="line {s.css}" d="{" ".join(path)}"/>')
        for x, y in pts:
            out.append(
                f'<circle class="hit" cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="7">'
                f"<title>{escape(s.label)} · day {x_label(x)}: {escape(s.fmt.format(y))}</title>"
                "</circle>"
            )
        lx, ly = sorted(pts)[-1]
        y_text = sy(ly) + 5
        for other in label_slots:
            if abs(other - y_text) < 22:
                y_text = other + 22 if y_text >= other else other - 22
        label_slots.append(y_text)
        out.append(f'<circle class="end {s.css}" cx="{sx(lx):.1f}" cy="{sy(ly):.1f}" r="4.5"/>')
        out.append(
            f'<text class="direct" x="{sx(lx) + 12:.1f}" y="{y_text:.1f}">'
            f'<tspan class="direct-name">{escape(s.label)}</tspan> '
            f"{escape(s.fmt.format(ly))}</text>"
        )
    for nx, ny, text in notes or []:
        out.append(f'<circle class="note-dot" cx="{sx(nx):.1f}" cy="{sy(ny):.1f}" r="9"/>')
        out.append(
            f'<text class="note" x="{sx(nx) - 14:.1f}" y="{sy(ny) + 5:.1f}" '
            f'text-anchor="end">{escape(text)}</text>'
        )
    out.append(
        f'<line class="axis" x1="{pad_l}" x2="{pad_l + plot_w}" '
        f'y1="{pad_t + plot_h}" y2="{pad_t + plot_h}"/>'
    )
    out.append("</svg>")
    return "\n".join(out)
