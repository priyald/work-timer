"""The pet itself, drawn as pixel grids.

No image files: each frame is a list of 16-character rows, one character per
pixel, which keeps the whole creature editable in a text editor and keeps the
app a single folder of Python.

The body is shared across moods and patched per mood (eyes, mouth, blush), and
the ears are swapped per animal. Hand-writing every combination would be forty
grids to keep in sync; this way there is one body to fix when it looks wrong.
"""

from __future__ import annotations

WIDTH = 16

# '.' transparent  O outline  F fur  D dark fur  W cream  E eye  N nose
# P pink  Z sleep
BODY = [
    "..OFFFOOOOFFFO..",
    ".OFFFFFFFFFFFFO.",
    ".OFFEFFFFFFEFFO.",     # 2: eyes
    ".OFFFFFFFFFFFFO.",     # 3: cheeks
    ".OFFFWWNNWWFFFO.",
    "..OFFWWWWWWFFO..",     # 5: muzzle / mouth
    "...OOWWWWWWOO...",
    "..OFFFFFFFFFFO..",
    ".OFFFFFFFFFFFFO.",
    ".OFFOOFFFFOOFFO.",
    "..OO..OOOO..OO..",
]

EARS = {
    "fox": ["................",
            "...OO......OO...",
            "..OFDO....ODFO..",
            "..OFFDO..ODFFO.."],
    "cat": ["................",
            "..OO........OO..",
            "..OFO......OFO..",
            "..OFFO....OFFO.."],
    "bunny": ["...OO......OO...",
              "...OPO....OPO...",
              "...OPO....OPO...",
              "..OFFO....OFFO.."],
}

BASE_COLOURS = {
    "O": (0.16, 0.10, 0.07, 1.0),
    "W": (0.98, 0.95, 0.90, 1.0),
    "E": (0.10, 0.07, 0.05, 1.0),
    "N": (0.24, 0.14, 0.12, 1.0),
    "P": (0.95, 0.62, 0.64, 1.0),
    "Z": (0.58, 0.62, 0.72, 1.0),
}

FUR = {
    "fox": {"F": (0.91, 0.47, 0.17, 1.0), "D": (0.72, 0.33, 0.10, 1.0)},
    "cat": {"F": (0.56, 0.56, 0.62, 1.0), "D": (0.42, 0.42, 0.48, 1.0)},
    "bunny": {"F": (0.96, 0.94, 0.92, 1.0), "D": (0.84, 0.81, 0.79, 1.0)},
}

CLOSED_EYES = {4: "O", 11: "O"}


def _swap(row: str, changes: dict) -> str:
    chars = list(row)
    for index, value in changes.items():
        chars[index] = value
    return "".join(chars)


def _body(mood: str) -> list:
    rows = list(BODY)
    if mood == "asleep":
        rows[2] = _swap(rows[2], CLOSED_EYES)
    elif mood == "happy":
        rows[1] = _swap(rows[1], {3: "O", 5: "O", 10: "O", 12: "O"})   # ^  ^
        rows[2] = _swap(rows[2], CLOSED_EYES)
        rows[3] = _swap(rows[3], {2: "P", 13: "P"})                    # blush
    elif mood == "eating":
        rows[2] = _swap(rows[2], CLOSED_EYES)
        rows[5] = _swap(rows[5], {7: "O", 8: "O"})                     # open mouth
    elif mood == "talking":
        rows[5] = _swap(rows[5], {7: "O"})
    return rows


def grid(animal: str, mood: str) -> list:
    ears = list(EARS.get(animal, EARS["fox"]))
    if mood == "asleep":
        ears[0] = _swap(ears[0], {14: "Z"})
    return ears + _body(mood)


def _bob(rows: list) -> list:
    """The same creature, one pixel lower. Alternating the two is the breathing."""
    return ["." * WIDTH] + rows[:-1]


def frames(animal: str, mood: str) -> list:
    """Eight frames, cycled about once a second. The last one blinks."""
    still = grid(animal, mood)
    cycle = [still, _bob(still)] * 4
    if mood in ("awake", "talking"):
        blinking = list(still)
        blinking[6] = _swap(blinking[6], CLOSED_EYES)   # row 2 of the body
        cycle[-1] = blinking
    return cycle


def colours(animal: str) -> dict:
    palette = dict(BASE_COLOURS)
    palette.update(FUR.get(animal, FUR["fox"]))
    return palette
