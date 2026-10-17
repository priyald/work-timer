"""Drives the schedule against a fake clock. Run: python3 tests/test_schedule.py

Both clocks are faked and advance together: the monotonic one the durations use,
and the wall clock the stops and meetings use. Without that, these tests would
pass or fail depending on what time of day you ran them.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from timer import config
from timer.schedule import Phase, Schedule

TUESDAY_9AM = dt.datetime(2026, 9, 15, 9, 0)
MONDAY_11AM = dt.datetime(2026, 9, 14, 11, 0)


class FakeClock:
    """One advance() moves elapsed time and the time of day together."""

    def __init__(self, start=TUESDAY_9AM):
        self.mono = 1000.0
        self.wall_now = start

    def mono_now(self):
        return self.mono

    def wall(self):
        return self.wall_now

    def advance(self, seconds):
        self.mono += seconds
        self.wall_now += dt.timedelta(seconds=seconds)


def build(start=TUESDAY_9AM):
    clock = FakeClock(start)
    return Schedule(config.load(), clock=clock.mono_now, wall=clock.wall), clock


def run_phase(sched, clock, over=1):
    """Sit out the rest of the current phase and return the phase that follows."""
    clock.advance((sched.remaining() or 0) + over)
    return sched.tick()


# --------------------------------------------------------------- core rhythm

def test_basic_cycle():
    sched, clock = build()
    assert sched.start() is Phase.WORK
    assert run_phase(sched, clock) is Phase.SHORT_BREAK
    assert run_phase(sched, clock) is Phase.WORK
    for _ in range(2):
        assert run_phase(sched, clock) is Phase.SHORT_BREAK
        assert run_phase(sched, clock) is Phase.WORK
    assert run_phase(sched, clock) is Phase.LONG_BREAK
    print("ok  basic cycle: 4 blocks then a long break")


def test_snooze_defers_the_break_then_pays_it():
    sched, clock = build()
    sched.start()
    assert run_phase(sched, clock) is Phase.SHORT_BREAK
    assert sched.snooze() is Phase.WORK
    assert round(sched.remaining()) == sched.cfg["snooze_minutes"] * 60
    assert run_phase(sched, clock) is Phase.SHORT_BREAK, "the owed break comes back"
    print("ok  snooze defers a break and still pays it")


def test_snoozing_twice_shifts_up_a_gear():
    sched, clock = build()
    assert sched.gear == "steady"
    sched.start()
    run_phase(sched, clock)
    sched.snooze()
    run_phase(sched, clock)
    sched.snooze()
    run_phase(sched, clock)
    assert sched.gear == "flow", sched.gear
    assert sched.gear_cfg["work_minutes"] == 50
    print("ok  two snoozes shift steady -> flow")


def test_bailing_early_twice_shifts_down_a_gear():
    sched, clock = build()
    sched.start()
    clock.advance(60)
    sched.break_now()
    run_phase(sched, clock)
    clock.advance(60)
    sched.break_now()
    assert sched.gear == "choppy", sched.gear
    print("ok  two early exits shift steady -> choppy")


def test_pause_preserves_the_remaining_time():
    sched, clock = build()
    sched.start()
    clock.advance(300)
    sched.pause()
    clock.advance(9999)
    assert sched.tick() is None, "a pause does not expire"
    sched.resume()
    assert sched.phase is Phase.WORK
    assert 1195 < sched.remaining() < 1205
    print("ok  pause holds the clock and restores what was left")


# ---------------------------------------------------------- starting at all

def test_five_minute_start_rolls_into_a_real_block():
    sched, clock = build()
    assert sched.start_small() is Phase.WORK
    assert round(sched.remaining()) == sched.cfg["small_start_minutes"] * 60
    assert run_phase(sched, clock) is Phase.WORK, "no break is thrown at you at 5 min"
    assert sched.rolled_from_small is True
    assert round(sched.remaining()) == sched.gear_cfg["work_minutes"] * 60
    assert sched.blocks_done == 0, "the 5 minutes does not owe you a break"
    print("ok  a 5 minute start quietly becomes a normal block")


# ----------------------------------------------------------- the two stops

def test_meal_on_hours_is_open_ended_and_resets_its_counter():
    sched, clock = build()
    sched.start()
    sched.worked_since_meal = sched.cfg["meal_after_work_hours"] * 3600
    assert run_phase(sched, clock) is Phase.MEAL
    assert sched.remaining() is None, "a meal waits for you, it does not count down"
    assert sched.back_to_work() is Phase.WORK
    assert sched.worked_since_meal == 0.0
    print("ok  meal on hours: open ended, resets the meal counter")


def test_lunch_fires_on_the_clock_without_five_hours():
    sched, clock = build(dt.datetime(2026, 9, 15, 12, 35))
    sched.start()
    clock.advance(25 * 60 + 1)          # 13:00, only 25 minutes worked
    assert sched.tick() is Phase.MEAL
    print("ok  13:00 triggers lunch even on a day that started late")


def test_lunch_does_not_fire_the_moment_you_sit_down():
    sched, clock = build(dt.datetime(2026, 9, 15, 13, 30))
    sched.start()
    clock.advance(5 * 60)               # only 5 minutes in, past 13:00 already
    assert sched.tick() is None, "no floor check means an instant lunch nag"
    clock.advance(16 * 60)              # now past the 20 minute floor
    assert sched.tick() is Phase.MEAL
    print("ok  the clock stop waits for the minimum-work floor first")


def test_day_stop_is_hard():
    sched, clock = build(dt.datetime(2026, 9, 15, 18, 5))
    sched.start()
    clock.advance(30 * 60)              # 18:35
    assert sched.tick() is Phase.DAY_DONE
    assert sched.back_to_work() is Phase.DAY_DONE, "there is no clicking past it"
    clock.advance(2 * 3600)
    assert sched.tick() is None
    assert sched.phase is Phase.DAY_DONE, "it does not quietly let you back in"
    assert sched.reset_day() is Phase.IDLE, "restarting the day is the only way out"
    print("ok  18:30 is a hard stop; only a deliberate restart reopens the day")


def test_lunch_does_not_ambush_you_in_the_evening():
    sched, clock = build(dt.datetime(2026, 9, 15, 18, 40))
    sched.start()
    clock.advance(25 * 60)
    assert sched.tick() is not Phase.MEAL, "18:40 is past 13:00 but is not lunch"
    print("ok  a missed lunch does not resurface at dinner time")


def test_day_stop_on_hours_beats_the_meal():
    sched, clock = build()
    sched.start()
    sched.worked_seconds = sched.cfg["stop_after_work_hours"] * 3600
    sched.worked_since_meal = sched.cfg["meal_after_work_hours"] * 3600
    assert run_phase(sched, clock) is Phase.DAY_DONE, "the day stop outranks the meal"
    print("ok  the 8h stop outranks the meal")


def test_stop_can_fire_during_a_break():
    sched, clock = build(dt.datetime(2026, 9, 15, 18, 0))
    sched.start()
    clock.advance(25 * 60 + 1)
    assert sched.tick() is Phase.SHORT_BREAK   # 18:25, break starts
    clock.advance(6 * 60)                      # 18:31, still on the break
    assert sched.tick() is Phase.DAY_DONE, "18:30 must not be swallowed by a break"
    print("ok  a clock stop landing mid-break still fires")


# ------------------------------------------------------------------ meetings

def test_monday_meeting_takes_over_and_counts_as_work():
    sched, clock = build(MONDAY_11AM)
    sched.start()
    clock.advance(15 * 60 + 1)                 # 11:15
    assert sched.tick() is Phase.MEETING
    assert sched.meeting["label"] == "Monday meeting"
    assert sched.remaining() is None, "no countdown during a call"
    before = sched.worked_today()
    clock.advance(30 * 60)
    assert sched.worked_today() > before + 1700, "meeting time counts as work"
    print("ok  the Monday meeting takes over at 11:15 and counts as work")


def test_meeting_ends_into_a_fresh_block_and_counts_as_one():
    sched, clock = build(MONDAY_11AM)
    sched.start()
    clock.advance(15 * 60 + 1)
    sched.tick()
    assert sched.phase is Phase.MEETING
    blocks = sched.blocks_done
    clock.advance(61 * 60)                     # 12:16, window closed
    assert sched.tick() is Phase.WORK
    assert sched.blocks_done == blocks + 1, "an hour on a call is a block"
    assert round(sched.remaining()) == sched.gear_cfg["work_minutes"] * 60
    print("ok  the meeting ends into a fresh block and counts as one")


def test_ending_a_meeting_early_does_not_drag_you_back():
    sched, clock = build(MONDAY_11AM)
    sched.start()
    clock.advance(15 * 60 + 1)
    sched.tick()
    assert sched.phase is Phase.MEETING
    assert sched.end_meeting() is Phase.WORK
    clock.advance(60)
    assert sched.tick() is None, "the window must not pull you straight back in"
    assert sched.phase is Phase.WORK
    print("ok  ending a call early sticks for the rest of the window")


def test_no_meeting_on_a_tuesday():
    sched, clock = build(dt.datetime(2026, 9, 15, 11, 14))
    sched.start()
    clock.advance(2 * 60)
    assert sched.tick() is None
    assert sched.phase is Phase.WORK
    print("ok  11:15 on a Tuesday is just work")


def test_worked_today_counts_the_block_in_progress():
    sched, clock = build()
    sched.start()
    clock.advance(600)
    assert 595 < sched.worked_today() < 605
    print("ok  today's total includes the block in progress")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("\nall schedule tests passed")
