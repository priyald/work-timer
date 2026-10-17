"""The animal, and every piece of wording tied to a phase.

One place for all the cosmetic strings so changing the character (or the tone
of the nudges) never means touching the timer logic.
"""

from __future__ import annotations

from .schedule import Phase

ANIMALS = {
    "fox": "\U0001F98A",
    "cat": "\U0001F431",
    "bunny": "\U0001F430",
    "frog": "\U0001F438",
    "otter": "\U0001F9A6",
    "penguin": "\U0001F427",
    "duck": "\U0001F424",
    "hedgehog": "\U0001F994",
}

# Which drawn expression each phase wears. The art lives in sprite.py.
MOODS = {
    Phase.IDLE: "asleep",
    Phase.WORK: "awake",
    Phase.MEETING: "talking",
    Phase.SHORT_BREAK: "happy",
    Phase.LONG_BREAK: "happy",
    Phase.MEAL: "eating",
    Phase.DAY_DONE: "asleep",
    Phase.PAUSED: "awake",
}

# Shown in the menu bar instead of the animal, so a glance tells you the phase.
GLYPHS = {
    Phase.IDLE: "\U0001F4A4",
    Phase.WORK: None,  # the animal itself
    Phase.MEETING: "\U0001F4AC",
    Phase.SHORT_BREAK: "☕",
    Phase.LONG_BREAK: "\U0001F33F",
    Phase.MEAL: "\U0001F35C",
    Phase.DAY_DONE: "\U0001F319",
    Phase.PAUSED: "⏸",
}

LABELS = {
    Phase.IDLE: "not started",
    Phase.WORK: "working",
    Phase.MEETING: "in a meeting",
    Phase.SHORT_BREAK: "short break",
    Phase.LONG_BREAK: "long break",
    Phase.MEAL: "meal — no timer",
    Phase.DAY_DONE: "done for today",
    Phase.PAUSED: "paused",
}

# (title, body) for the notification that fires when a phase begins.
ANNOUNCEMENTS = {
    Phase.SHORT_BREAK: ("Short break", "Stand up, look away. It restarts itself."),
    Phase.LONG_BREAK: ("Long break", "Properly leave the desk for this one."),
    Phase.MEAL: ("Eat something", "No countdown. Tell the timer when you're back."),
    Phase.DAY_DONE: ("That's the day", "You've hit your hours. Stop here."),
    Phase.WORK: ("Back to it", None),
    Phase.MEETING: ("Meeting time", "Counted as work. No breaks until it's done."),
}

SOUNDS = {
    Phase.SHORT_BREAK: "Tink",
    Phase.LONG_BREAK: "Glass",
    Phase.MEAL: "Submarine",
    Phase.DAY_DONE: "Hero",
    Phase.WORK: "Pop",
    Phase.MEETING: "Morse",
}

# Said when the five minute start quietly turns into a real block.
ROLLED_FROM_SMALL = ("That's your five",
                     "Stop whenever you like. It'll keep counting until you do.")

GEAR_NOTES = {
    "choppy": "Shorter blocks — 15 min on, 5 off.",
    "steady": "Back to 25 min blocks.",
    "flow": "You're in flow. Blocks are 50 min now.",
}


def animal(name: str) -> str:
    return ANIMALS.get(name, ANIMALS["fox"])


def menu_glyph(name: str, phase: Phase) -> str:
    return GLYPHS.get(phase) or animal(name)


def mood(phase: Phase) -> str:
    return MOODS.get(phase, "awake")


def label(phase: Phase) -> str:
    return LABELS.get(phase, "")
