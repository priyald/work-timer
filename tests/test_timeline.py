"""Run: python3 tests/test_timeline.py"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from timer import timeline

MEETINGS = [{"label": "Monday meeting", "days": ["mon"], "start": "11:15", "end": "12:15"}]

# 2026-09-14 is a Monday; the 15th is a Tuesday.
MON = dt.date(2026, 9, 14)
TUE = dt.date(2026, 9, 15)


def at(day, hour, minute):
    return dt.datetime.combine(day, dt.time(hour, minute))


def test_parsing():
    assert timeline.parse_hhmm("13:00") == dt.time(13, 0)
    assert timeline.parse_hhmm(None) is None
    assert timeline.parse_hhmm("nonsense") is None
    print("ok  clock times parse, and bad ones return None instead of raising")


def test_clock_threshold():
    assert not timeline.at_or_past(at(MON, 12, 59), "13:00")
    assert timeline.at_or_past(at(MON, 13, 0), "13:00")
    assert not timeline.at_or_past(at(MON, 20, 0), None), "no time set means never"
    print("ok  at_or_past, and an unset time never fires")


def test_meeting_window():
    assert timeline.current_meeting(at(MON, 11, 0), MEETINGS) is None
    assert timeline.current_meeting(at(MON, 11, 15), MEETINGS)["label"] == "Monday meeting"
    assert timeline.current_meeting(at(MON, 12, 14), MEETINGS) is not None
    assert timeline.current_meeting(at(MON, 12, 15), MEETINGS) is None, "end is exclusive"
    assert timeline.current_meeting(at(TUE, 11, 30), MEETINGS) is None, "Tuesday is not Monday"
    print("ok  the Monday window opens at 11:15, closes at 12:15, and only on Mondays")


def test_meeting_end():
    meeting = MEETINGS[0]
    assert timeline.meeting_end(at(MON, 11, 30), meeting) == at(MON, 12, 15)
    print("ok  meeting end resolves to a datetime today")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("\nall timeline tests passed")
