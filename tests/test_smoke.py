"""Builds the real panels, status item and controller, and renders every phase
without starting the event loop. Catches selector and bridging mistakes that
only show up at runtime. Run: python3 tests/test_smoke.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AppKit import NSApplicationActivationPolicyAccessory

from timer import actions
from timer.app import build
from timer.schedule import Phase

# Exercise the real startup path, minus the event loop. This is where a retain
# bug or a bad selector surfaces.
app, controller = build()
assert app.activationPolicy() == NSApplicationActivationPolicyAccessory
print("ok  build(): widget, edge tab, status item, tick timer, no dock icon")

for phase in Phase:
    open_ended = phase in (Phase.IDLE, Phase.MEAL, Phase.DAY_DONE,
                           Phase.PAUSED, Phase.MEETING)
    controller.schedule._enter(phase, None if open_ended else 300)
    controller.render()
    primary, secondary = actions.buttons(controller.schedule)
    shown = (primary[0] if primary else "-", secondary[0] if secondary else "-")
    print(f"ok  render {phase.value:<12} primary={shown[0]!r:<14} secondary={shown[1]!r}")

# Exhausted snoozes must not offer another one.
controller.schedule._enter(Phase.SHORT_BREAK, 300)
controller.schedule.snoozes = controller.schedule.cfg["max_snoozes_per_break"]
controller.render()
assert actions.buttons(controller.schedule)[0][0] == "Back to it"
print("ok  spent snoozes swap the button instead of lying")

# Button paths, as the UI would call them.
controller.reset_day()
controller.do_primary()
assert controller.schedule.phase is Phase.WORK
controller.do_secondary()
assert controller.schedule.phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK)
controller.do_primary()
assert controller.schedule.phase is Phase.WORK, "snooze sends you back to work"
print("ok  start -> break now -> snooze all fire through the real handlers")

# The hard stop offers no button at all, and clicking through it does nothing.
controller.schedule._enter(Phase.DAY_DONE, None)
assert actions.buttons(controller.schedule) == (None, None)
controller.render()
controller.do_primary()
controller.do_secondary()
assert controller.schedule.phase is Phase.DAY_DONE, "the stop must not be clickable"
print("ok  the 8h stop has no buttons and cannot be clicked past")

for gear in ("flow", "choppy", "steady"):
    controller.set_gear(gear)
assert controller.schedule.gear == "steady"
controller.toggle_adapt(); controller.toggle_adapt()
print("ok  menu handlers: gear and adapt")

# ---------------------------------------------------------------- the display

# The widget is fixed: it is there on the desktop and it is still there,
# unmoved, when an app is in front. Only the tab comes and goes.
HOME = controller.widget.position()
controller.widget.set_position({"display": HOME["display"], "dx": 300.0, "dy": 200.0})
PINNED = controller.widget.position()
assert (PINNED["dx"], PINNED["dy"]) == (300.0, 200.0), PINNED
controller.on_frontmost_change(True)
assert controller.widget.is_visible()
assert not controller.tab.is_visible(), "no tab needed while you can see the widget"

controller.on_frontmost_change(False)
assert controller.widget.is_visible(), "the widget must not vanish inside an app"
assert controller.widget.position() == PINNED, controller.widget.position()
assert controller.tab.is_visible() and not controller.tab.is_expanded()
print("ok  the widget stays put and stays visible; the tab appears inside apps")

controller.expand()
assert controller.tab.is_expanded()
controller.collapse()
assert not controller.tab.is_expanded()
controller.expand()
controller.collapseNow_(None)
assert not controller.tab.is_expanded(), "it collapses on its own too"
assert controller.widget.position() == PINNED, "none of that moved the widget"
print("ok  tab expands, collapses by hand and by timeout, widget unaffected")

controller.toggle_pet()
assert not controller.widget.is_visible() and not controller.tab.is_visible()
controller.toggle_pet()
assert controller.widget.is_visible()
print("ok  hiding the pet hides both panels")

# The widget is a timer until you click it, then it is a timer with controls.
controller.on_frontmost_change(True)
controller.reset_day()
assert not controller.widget.is_open()
assert controller.widget._restart.isHidden(), "no controls until you ask for them"
SHUT_AT = controller.widget.position()

controller.widget._background.mouseDown_(None)
controller.widget._background.mouseUp_(None)
assert controller.widget.is_open(), "clicking the widget opens the controls"
assert not controller.widget._restart.isHidden()
assert controller.widget.position() == SHUT_AT, "opening must not walk it down the screen"

controller.closeWidgetNow_(None)
assert not controller.widget.is_open(), "and they close themselves again"
assert controller.widget.position() == SHUT_AT
print("ok  widget shows the timer; clicking it opens the controls")

def finish_a_drag():
    """The real mouseUp path, with the drag flag already set the way a genuine
    mouseDragged would have set it."""
    background = controller.widget._background
    background.mouseDown_(None)
    background._dragged = True
    background.mouseUp_(None)


# Anything that means "you have moved on" closes the controls again.
for label, moved_on in (
    ("a display change", lambda: controller.screensChanged_(None)),
    ("switching to an app", lambda: controller.on_frontmost_change(False)),
    ("dragging it somewhere", finish_a_drag),
):
    controller.on_frontmost_change(True)
    controller.widget.set_open(True)
    assert controller.widget.is_open()
    moved_on()
    assert not controller.widget.is_open(), label
    assert controller.widget.position() == SHUT_AT, label
print("ok  display change, app switch and a drag all close the controls")

# Restart takes one press and returns it to the start position.
controller.widget.set_open(True)
controller.do_primary()
controller.schedule.pause()
controller.schedule.worked_seconds = 3600.0
controller.widget._restart.performClick_(None)
assert controller.schedule.phase is Phase.IDLE, "one press, back to the start"
assert controller.schedule.worked_seconds == 0.0
assert controller.schedule._paused_remaining is None, "no resume left over from before"
assert actions.buttons(controller.schedule)[0][0] == "Start"
print("ok  one press on restart returns it to Start with nothing carried over")

# A monitor being plugged in or out must not drift the widget off its display.
controller.screensChanged_(None)
assert controller.widget.position() == PINNED, controller.widget.position()
print("ok  a screen rearrangement leaves the widget on its own display")

controller._persist()
assert (Path(__file__).resolve().parent.parent / ".today.json").exists()
controller.reset_day()
print("ok  today's state persisted\n\nsmoke test passed")
