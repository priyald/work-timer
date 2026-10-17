"""Wall-clock helpers: known meeting windows, and 'is it past 13:00 yet'.

Separate from schedule.py because the schedule reasons in elapsed seconds
(monotonic, immune to the clock changing) while these questions are about the
actual time of day. Mixing the two in one file is how you end up with a timer
that jumps an hour on a DST change.
"""

from __future__ import annotations

import datetime as dt

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_hhmm(value):
    """'13:00' -> datetime.time, or None if it is missing or malformed."""
    if not value:
        return None
    try:
        hour, minute = str(value).split(":")
        return dt.time(int(hour), int(minute))
    except (ValueError, TypeError):
        return None


def at_or_past(now: dt.datetime, hhmm) -> bool:
    """Has the clock reached this time today?"""
    moment = parse_hhmm(hhmm)
    if moment is None:
        return False
    return now.time() >= moment


def within_window(now: dt.datetime, hhmm, minutes: int) -> bool:
    """Is it between this time and this time plus a window?

    A threshold alone is not enough for lunch: "it is past 13:00" is still true
    at 18:36, and a lunch reminder then is noise.
    """
    start_time = parse_hhmm(hhmm)
    if start_time is None or not minutes:
        return False
    start = dt.datetime.combine(now.date(), start_time)
    return start <= now < start + dt.timedelta(minutes=minutes)


def _covers(now: dt.datetime, meeting: dict) -> bool:
    days = [d.lower()[:3] for d in meeting.get("days", [])]
    if days and DAY_NAMES[now.weekday()] not in days:
        return False
    start = parse_hhmm(meeting.get("start"))
    end = parse_hhmm(meeting.get("end"))
    if start is None or end is None:
        return False
    return start <= now.time() < end


def current_meeting(now: dt.datetime, meetings) -> dict | None:
    """The meeting happening right now, if any."""
    for meeting in meetings or []:
        if _covers(now, meeting):
            return meeting
    return None


def meeting_end(now: dt.datetime, meeting: dict) -> dt.datetime | None:
    end = parse_hhmm(meeting.get("end"))
    if end is None:
        return None
    return dt.datetime.combine(now.date(), end)
