"""Run: python3 tests/test_sprite.py

Grid integrity matters more than it looks: one short row draws a creature with a
bite out of it, and one stray character draws nothing at all.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from timer import pet, sprite
from timer.schedule import Phase

MOODS = ("awake", "asleep", "happy", "eating", "talking")


def test_every_grid_is_rectangular():
    for animal in sprite.EARS:
        for mood in MOODS:
            rows = sprite.grid(animal, mood)
            assert len(rows) == 15, (animal, mood, len(rows))
            assert all(len(r) == sprite.WIDTH for r in rows), (animal, mood)
    print("ok  every animal and mood is a clean 16x15 grid")


def test_no_character_is_missing_a_colour():
    for animal in sprite.EARS:
        palette = sprite.colours(animal)
        for mood in MOODS:
            for row in sprite.grid(animal, mood):
                for char in row:
                    assert char == "." or char in palette, (animal, mood, char)
    print("ok  every drawn character has a colour")


def test_moods_actually_differ():
    awake = sprite.grid("fox", "awake")
    for mood in ("asleep", "happy", "eating"):
        assert sprite.grid("fox", mood) != awake, mood
    print("ok  the moods are visibly different from each other")


def test_animals_actually_differ():
    fox = sprite.grid("fox", "awake")
    assert sprite.grid("cat", "awake") != fox
    assert sprite.grid("bunny", "awake") != fox
    assert sprite.grid("nonsense", "awake") == fox, "unknown animals fall back to the fox"
    print("ok  fox, cat and bunny differ, and an unknown name falls back")


def test_frames_animate_and_stay_rectangular():
    for mood in MOODS:
        cycle = sprite.frames("fox", mood)
        assert len(cycle) == 8
        assert cycle[0] != cycle[1], "the bob has to actually move"
        for frame in cycle:
            assert len(frame) == 15
            assert all(len(r) == sprite.WIDTH for r in frame)
    assert sprite.frames("fox", "awake")[-1] != sprite.frames("fox", "awake")[0], "blink"
    print("ok  eight frames per mood, all rectangular, awake blinks")


def test_every_phase_maps_to_a_real_mood():
    for phase in Phase:
        assert pet.mood(phase) in MOODS, phase
    print("ok  every phase has a drawn expression")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("\nall sprite tests passed")
