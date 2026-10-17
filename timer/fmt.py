"""Time formatting. Two shapes: a countdown, and a human span."""

from __future__ import annotations


def clock(seconds: float | None) -> str:
    """Countdown for the big readout: 04:59, or 1:04:59 once it passes an hour."""
    if seconds is None:
        return "—"
    total = int(max(0.0, seconds) + 0.5)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def span(seconds: float) -> str:
    """Human total for 'worked today': 45m, 2h 14m."""
    total = int(max(0.0, seconds))
    hours, minutes = divmod(total // 60, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"
