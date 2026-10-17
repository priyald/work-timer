"""What the two buttons mean in each phase.

Split out of app.py so the wording and the wiring sit side by side and stay in
sync: one table, read by both the pet and the menu bar.

Each entry is (pet label, menu label, method name on Schedule). A None entry
means that button is hidden in that phase.
"""

from __future__ import annotations

from .schedule import Phase

PRIMARY = {
    Phase.IDLE: ("Start", "Start working", "start"),
    Phase.WORK: ("Pause", "Pause", "pause"),
    Phase.MEETING: ("Pause", "Pause", "pause"),
    Phase.PAUSED: ("Resume", "Resume", "resume"),
    Phase.SHORT_BREAK: ("+10 min", "+10 more minutes (I'm in flow)", "snooze"),
    Phase.LONG_BREAK: ("+10 min", "+10 more minutes (I'm in flow)", "snooze"),
    Phase.MEAL: ("I'm back", "I'm back", "back_to_work"),
    # No entry for DAY_DONE on purpose: the hard stop offers no way onward.
}

SECONDARY = {
    # Five minutes is a much cheaper thing to agree to than twenty five, and
    # getting started is the hard part, so it gets its own button.
    Phase.IDLE: ("Just 5 min", "Just do 5 minutes", "start_small"),
    Phase.WORK: ("Break", "Break now", "break_now"),
    Phase.MEETING: ("Done", "Meeting's over", "end_meeting"),
    Phase.PAUSED: ("Break", "Break now", "break_now"),
    Phase.SHORT_BREAK: ("Skip", "Skip the break", "skip_break"),
    Phase.LONG_BREAK: ("Skip", "Skip the break", "skip_break"),
    Phase.MEAL: ("End day", "Stop for today", "stop_for_today"),
    Phase.DAY_DONE: None,
}

# Once you've used up your snoozes, offering another one is a lie. The break
# becomes the primary button instead, and pausing moves to the second slot.
SNOOZES_SPENT_PRIMARY = ("Back to it", "Back to work", "skip_break")
SNOOZES_SPENT_SECONDARY = ("Pause", "Pause", "pause")


def buttons(schedule):
    """Return (primary, secondary) for the phase, either being None when that
    button should not exist. DAY_DONE has neither: that is the point of it."""
    phase = schedule.phase
    primary = PRIMARY.get(phase)
    secondary = SECONDARY.get(phase)
    spent = schedule.snoozes >= schedule.cfg["max_snoozes_per_break"]
    if phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK) and spent:
        primary = SNOOZES_SPENT_PRIMARY
        secondary = SNOOZES_SPENT_SECONDARY
    return primary, secondary
