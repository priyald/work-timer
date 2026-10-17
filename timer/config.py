"""Loading and saving user settings.

Kept deliberately dumb: a dict with dotted-ish accessors and a merge against
DEFAULTS, so a half-written config.json still starts the app instead of
crashing it. Any key the user deletes falls back to the default.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / ".today.json"

DEFAULTS = {
    "mode": "steady",
    "adapt_mode": True,
    "gears": {
        "choppy": {"work_minutes": 15, "short_break_minutes": 5, "blocks_before_long_break": 6},
        "steady": {"work_minutes": 25, "short_break_minutes": 5, "blocks_before_long_break": 4},
        "flow": {"work_minutes": 50, "short_break_minutes": 10, "blocks_before_long_break": 2},
    },
    "long_break_minutes": 30,
    "meal_after_work_hours": 5,
    "lunch_by": "13:00",
    "lunch_window_minutes": 150,
    "stop_after_work_hours": 8,
    "stop_by": "18:30",
    "min_work_before_clock_stop_minutes": 20,
    "small_start_minutes": 5,
    "meetings": [],
    "snooze_minutes": 10,
    "max_snoozes_per_break": 3,
    "auto_start_after_break": True,
    "animal": "fox",
    "sounds": True,
    "notifications": True,
}

GEAR_ORDER = ["choppy", "steady", "flow"]


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load() -> dict:
    """Read config.json, falling back to defaults for anything missing or broken."""
    try:
        raw = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return dict(DEFAULTS)
    if not isinstance(raw, dict):
        return dict(DEFAULTS)
    return _merge(DEFAULTS, raw)


def save_mode(mode: str) -> None:
    """Persist a gear change so tomorrow starts where today left off."""
    try:
        raw = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        raw = {}
    raw["mode"] = mode
    try:
        CONFIG_PATH.write_text(json.dumps(raw, indent=2) + "\n")
    except OSError:
        pass


def load_today() -> dict:
    """Today's accumulated totals, so a restart mid-afternoon doesn't reset your day."""
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def save_today(state: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    except OSError:
        pass
