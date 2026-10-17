"""The break schedule, as a pure state machine.

No AppKit in here on purpose. Everything about *when* something happens lives in
this file and can be tested by driving a fake clock, which matters because the
adaptive gear-shifting and the two-sided stops are the fiddly parts.

Two clocks, deliberately kept apart. Durations use a monotonic clock so a DST
change or an NTP correction cannot make a block jump. Stops and meetings use
wall-clock time, because "lunch by 13:00" is a question about the actual day.

Shape of a day:

    WORK -> SHORT_BREAK -> WORK -> ... -> LONG_BREAK -> ...
    a known meeting window   -> MEETING  (counts as work, never interrupted)
    5h of work OR 13:00      -> MEAL     (open ended)
    8h of work OR 18:30      -> DAY_DONE (terminal)

MEAL waits until you say you're back. DAY_DONE is a hard stop: there is no
"one more hour" button, because a stop you can wave away in one tap is not a
stop. The only way out is a deliberate restart of the day.
"""

from __future__ import annotations

import datetime as dt
import time
from enum import Enum

from . import timeline
from .config import GEAR_ORDER


class Phase(Enum):
    IDLE = "idle"
    WORK = "work"
    MEETING = "meeting"
    SHORT_BREAK = "short break"
    LONG_BREAK = "long break"
    MEAL = "meal"
    DAY_DONE = "day done"
    PAUSED = "paused"


BREAKS = {Phase.SHORT_BREAK, Phase.LONG_BREAK}
WORKING = {Phase.WORK, Phase.MEETING}          # time here counts as work
OPEN_ENDED = {Phase.IDLE, Phase.MEAL, Phase.DAY_DONE, Phase.PAUSED}
# A meeting can interrupt these. Not a meal, a finished day, or a manual pause.
INTERRUPTIBLE = {Phase.IDLE, Phase.WORK, Phase.SHORT_BREAK, Phase.LONG_BREAK}

# How many same-direction signals it takes to change gear. Two is enough to mean
# something and low enough that the app keeps up with your actual day.
SHIFT_AT = 2

# A meeting this long or longer counts as one work block toward the long break.
MEETING_COUNTS_AS_BLOCK_AFTER = 15 * 60


class Schedule:
    def __init__(self, cfg: dict, clock=time.monotonic, wall=None):
        self.cfg = cfg
        self._clock = clock
        self._wall = wall or dt.datetime.now

        self.phase = Phase.IDLE
        self.deadline: float | None = None
        self.gear: str = cfg.get("mode", "steady")
        if self.gear not in cfg["gears"]:
            self.gear = "steady"

        self.worked_seconds = 0.0        # real work time today
        self.worked_since_meal = 0.0
        self.blocks_done = 0             # since the last long break
        self.snoozes = 0                 # against the break currently owed
        self.drift = 0                   # + wants longer blocks, - wants shorter
        self.last_gear_change: str | None = None
        self.rolled_from_small = False   # the 5 minute start just became a real block
        self.meeting: dict | None = None

        self._entered_at = self._clock()
        self._pending_break: Phase | None = None
        self._is_snooze_stint = False
        self._is_small_start = False
        self._paused_remaining: float | None = None
        self._paused_phase: Phase | None = None
        self._lunch_fired_on: dt.date | None = None
        self._meeting_dismissed_until: dt.datetime | None = None

    # ---------------------------------------------------------------- queries

    def remaining(self) -> float | None:
        """Seconds left in this phase, or None when the phase is open ended."""
        if self.deadline is None:
            return None
        return max(0.0, self.deadline - self._clock())

    def progress(self) -> float | None:
        """How far through this phase, 0 to 1, or None when it is open ended."""
        if self.deadline is None:
            return None
        total = self.deadline - self._entered_at
        if total <= 0:
            return None
        return min(1.0, max(0.0, self.elapsed_in_phase() / total))

    def elapsed_in_phase(self) -> float:
        return self._clock() - self._entered_at

    def worked_today(self) -> float:
        """Work time today, including the block currently in progress."""
        extra = self.elapsed_in_phase() if self.phase in WORKING else 0.0
        return self.worked_seconds + extra

    @property
    def gear_cfg(self) -> dict:
        return self.cfg["gears"][self.gear]

    def next_break_label(self) -> str:
        """What the next break will be, for the menu. Best effort, not a promise."""
        if self.phase is Phase.MEETING:
            return "after the meeting"
        if self._pending_break is not None:
            return self._pending_break.value
        if self.worked_today() >= self.cfg["stop_after_work_hours"] * 3600:
            return "stop for the day"
        since_meal = self.worked_since_meal + (
            self.elapsed_in_phase() if self.phase in WORKING else 0.0)
        if since_meal >= self.cfg["meal_after_work_hours"] * 3600:
            return "meal"
        if self.blocks_done + 1 >= self.gear_cfg["blocks_before_long_break"]:
            return "long break"
        return "short break"

    # ---------------------------------------------------------------- actions

    def start(self) -> Phase:
        if self.phase is Phase.PAUSED:
            return self.resume()
        return self._enter(Phase.WORK, self.gear_cfg["work_minutes"] * 60)

    def start_small(self) -> Phase:
        """Five minutes is cheap to agree to. It rolls into a normal block after."""
        self._is_small_start = True
        return self._enter(Phase.WORK, self.cfg["small_start_minutes"] * 60)

    def pause(self) -> Phase:
        if self.phase in OPEN_ENDED:
            return self.phase
        self._paused_remaining = self.remaining()
        self._paused_phase = self.phase if self.phase is not Phase.MEETING else Phase.WORK
        self._bank_work()
        self._dismiss_meeting()
        return self._enter(Phase.PAUSED, None)

    def resume(self) -> Phase:
        phase = self._paused_phase or Phase.WORK
        seconds = self._paused_remaining
        self._paused_phase = None
        self._paused_remaining = None
        return self._enter(phase, seconds)

    def break_now(self) -> Phase:
        """You tapped out of a work block early: a vote for shorter blocks."""
        if self.phase is Phase.MEETING:
            self._dismiss_meeting()
        elif self.phase is not Phase.WORK:
            return self.phase
        if not self._is_snooze_stint:
            self.drift -= 1
        return self._finish_work()

    def snooze(self) -> Phase:
        """'+10, I'm in flow.' A vote for longer blocks, capped so it can't run forever."""
        if self.phase not in BREAKS:
            return self.phase
        if self.snoozes >= self.cfg["max_snoozes_per_break"]:
            return self.phase
        self.snoozes += 1
        self.drift += 1
        self._pending_break = self.phase
        self._is_snooze_stint = True
        return self._enter(Phase.WORK, self.cfg["snooze_minutes"] * 60)

    def back_to_work(self) -> Phase:
        """'I'm ready.' Ends a meal, or a break, early. Never ends the day stop."""
        now = self._wall()
        if self.phase is Phase.DAY_DONE:
            return self.phase
        if self.phase is Phase.MEAL:
            self.worked_since_meal = 0.0
            self._lunch_fired_on = now.date()
        self.snoozes = 0
        self._pending_break = None
        return self._enter(Phase.WORK, self.gear_cfg["work_minutes"] * 60)

    def skip_break(self) -> Phase:
        if self.phase in BREAKS:
            return self.back_to_work()
        return self.phase

    def end_meeting(self) -> Phase:
        """The call finished early. Don't drag me back into it."""
        if self.phase is not Phase.MEETING:
            return self.phase
        self._dismiss_meeting()
        self._bank_work()
        return self._enter(Phase.WORK, self.gear_cfg["work_minutes"] * 60)

    def stop_for_today(self) -> Phase:
        self._bank_work()
        self._dismiss_meeting()
        return self._enter(Phase.DAY_DONE, None)

    def reset_day(self) -> Phase:
        """Back to the start, with nothing carried over.

        Every field, not just the visible ones: a half-finished pause or a break
        still owed would otherwise survive the reset and surface later as a
        Resume button for a block that no longer exists.
        """
        self.worked_seconds = 0.0
        self.worked_since_meal = 0.0
        self.blocks_done = 0
        self.snoozes = 0
        self.drift = 0
        self.last_gear_change = None
        self.rolled_from_small = False
        self._pending_break = None
        self._is_snooze_stint = False
        self._is_small_start = False
        self._paused_phase = None
        self._paused_remaining = None
        self._lunch_fired_on = None
        self._dismiss_meeting()
        return self._enter(Phase.IDLE, None)

    def set_gear(self, gear: str) -> None:
        if gear in self.cfg["gears"]:
            self.gear = gear
            self.drift = 0

    # ------------------------------------------------------------------ clock

    def tick(self) -> Phase | None:
        """Advance time. Returns the new phase if one just started, else None."""
        moved = self._sync_meeting()
        if moved is not None:
            return moved
        # Also checked during a break: 18:30 landing mid-break should not be
        # swallowed until the next work block starts.
        if self.phase is Phase.WORK or self.phase in BREAKS:
            forced = self._check_clock_stops()
            if forced is not None:
                return forced
        if self.deadline is None or self._clock() < self.deadline:
            return None
        if self.phase is Phase.WORK:
            return self._finish_work()
        if self.phase in BREAKS:
            if self.cfg["auto_start_after_break"]:
                return self.back_to_work()
            return self._enter(Phase.IDLE, None)
        return None

    # --------------------------------------------------------------- meetings

    def _dismiss_meeting(self):
        """Stop the current meeting window from pulling us straight back in."""
        now = self._wall()
        current = timeline.current_meeting(now, self.cfg.get("meetings", []))
        if current:
            self._meeting_dismissed_until = timeline.meeting_end(now, current)
        self.meeting = None

    def _sync_meeting(self) -> Phase | None:
        now = self._wall()
        current = timeline.current_meeting(now, self.cfg.get("meetings", []))
        if self._meeting_dismissed_until and now < self._meeting_dismissed_until:
            current = None

        if current and self.phase in INTERRUPTIBLE:
            self._bank_work()
            self.meeting = current
            return self._enter(Phase.MEETING, None)
        if not current and self.phase is Phase.MEETING:
            was_long = self.elapsed_in_phase() >= MEETING_COUNTS_AS_BLOCK_AFTER
            self._bank_work()
            self.meeting = None
            if was_long:
                self.blocks_done += 1
            return self._enter(Phase.WORK, self.gear_cfg["work_minutes"] * 60)
        return None

    # ------------------------------------------------------------ hard  stops

    def _check_clock_stops(self) -> Phase | None:
        """The stops also fire on the clock, not only on hours worked, because a
        day that started at noon still ends in the evening."""
        now = self._wall()
        floor = self.cfg["min_work_before_clock_stop_minutes"] * 60
        if self.worked_today() < floor:
            return None

        if timeline.at_or_past(now, self.cfg.get("stop_by")):
            self._bank_work()
            return self._enter(Phase.DAY_DONE, None)

        if (self._lunch_fired_on != now.date()
                and timeline.within_window(now, self.cfg.get("lunch_by"),
                                           self.cfg.get("lunch_window_minutes"))):
            self._lunch_fired_on = now.date()
            self._bank_work()
            return self._enter(Phase.MEAL, None)
        return None

    # --------------------------------------------------------------- internal

    def _bank_work(self) -> None:
        if self.phase in WORKING:
            spent = self.elapsed_in_phase()
            self.worked_seconds += spent
            self.worked_since_meal += spent

    def _finish_work(self) -> Phase:
        self._bank_work()

        # The five minute start just quietly becomes a real block. No break, no
        # ceremony, and it does not count as a block you owe a break for.
        if self._is_small_start:
            self._is_small_start = False
            self.rolled_from_small = True
            return self._enter(Phase.WORK, self.gear_cfg["work_minutes"] * 60)

        was_snooze = self._is_snooze_stint
        self._is_snooze_stint = False
        if not was_snooze:
            self.blocks_done += 1

        now = self._wall()
        # Hard stops win over everything else.
        if self.worked_seconds >= self.cfg["stop_after_work_hours"] * 3600:
            return self._enter(Phase.DAY_DONE, None)
        if self.worked_since_meal >= self.cfg["meal_after_work_hours"] * 3600:
            self._lunch_fired_on = now.date()
            return self._enter(Phase.MEAL, None)

        # A break you snoozed is still owed.
        if self._pending_break is not None:
            owed, self._pending_break = self._pending_break, None
            return self._start_break(owed)

        if self.blocks_done >= self.gear_cfg["blocks_before_long_break"]:
            self.blocks_done = 0
            return self._start_break(Phase.LONG_BREAK)
        return self._start_break(Phase.SHORT_BREAK)

    def _start_break(self, phase: Phase) -> Phase:
        self._maybe_shift_gear()
        self.snoozes = 0
        minutes = (self.cfg["long_break_minutes"] if phase is Phase.LONG_BREAK
                   else self.gear_cfg["short_break_minutes"])
        return self._enter(phase, minutes * 60)

    def _maybe_shift_gear(self) -> None:
        """Let repeated snoozes lengthen blocks, and early exits shorten them."""
        self.last_gear_change = None
        if not self.cfg.get("adapt_mode", True):
            return
        if abs(self.drift) < SHIFT_AT:
            return
        step = 1 if self.drift > 0 else -1
        index = GEAR_ORDER.index(self.gear)
        new_index = max(0, min(len(GEAR_ORDER) - 1, index + step))
        self.drift = 0
        if new_index == index:
            return
        self.gear = GEAR_ORDER[new_index]
        self.last_gear_change = self.gear

    def _enter(self, phase: Phase, seconds: float | None) -> Phase:
        self.phase = phase
        self._entered_at = self._clock()
        self.deadline = None if seconds is None else self._entered_at + seconds
        return phase
