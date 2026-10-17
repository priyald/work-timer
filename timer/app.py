"""Wiring: schedule -> screen, clicks -> schedule, and saving the day.

The only module that knows about all the others. Everything here is either a
render pass or a one-line delegation, by design.

Two panels, deliberately independent. The desktop widget is fixed in place on
the wallpaper and never moves; the edge tab appears only while you are inside an
app, which is when the widget is covered. Earlier this was one panel changing
shape, and the cost was a widget that wandered off every time you switched apps.
"""

from __future__ import annotations

import datetime as dt

import objc
from AppKit import (NSApplication, NSApplicationActivationPolicyAccessory,
                    NSRunLoopCommonModes, NSTimer)
from Foundation import NSNotificationCenter, NSObject, NSRunLoop
from PyObjCTools import AppHelper

from . import actions, config, fmt, notify, pet, sprite
from .edgetab import EdgeTab
from .menubar import MenuBar
from .presence import Presence
from .schedule import OPEN_ENDED, Phase, Schedule
from .widget import DesktopWidget

SAVE_EVERY = 20        # ticks, so roughly every 20 seconds
COLLAPSE_AFTER = 10.0  # seconds an expanded tab stays open
WIDGET_OPEN_FOR = 12.0  # seconds the widget's controls stay open


class AppController(NSObject):

    def init(self):
        self = objc.super(AppController, self).init()
        if self is None:
            return None
        self.cfg = config.load()
        self.schedule = Schedule(self.cfg)
        self._ticks = 0
        self._collapse_timer = None
        self._hidden = False

        clicks = {"primary": self.do_primary,
                  "secondary": self.do_secondary,
                  "restart": self.reset_day}
        self.widget = DesktopWidget.alloc().init()
        self.widget.set_handlers(dict(clicks, opened=self.widget_opened))
        self._widget_timer = None
        self.tab = EdgeTab.alloc().init()
        self.tab.set_handlers(dict(clicks, expand=self.expand, collapse=self.collapse))

        self.menubar = MenuBar.alloc().init()
        self.menubar.set_handlers({"primary": self.do_primary,
                                   "secondary": self.do_secondary,
                                   "gear": self.set_gear,
                                   "adapt": self.toggle_adapt,
                                   "pet": self.toggle_pet,
                                   "reset": self.reset_day,
                                   "quit": self.quit})

        self.presence = Presence.alloc().init()
        self.presence.set_callback(self.on_frontmost_change)
        # Plugging a monitor in or out rearranges every screen's coordinates,
        # so both panels have to be told where they now belong.
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "screensChanged:",
            "NSApplicationDidChangeScreenParametersNotification", None)

        self._restore()
        self._apply_visibility(self.presence.is_desktop())
        self.render()
        return self

    # -------------------------------------------------------------- lifecycle

    def startTicking(self):
        timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, "onTick:", None, True)
        # Common modes so the countdown keeps running while a menu is open.
        NSRunLoop.currentRunLoop().addTimer_forMode_(timer, NSRunLoopCommonModes)
        self._timer = timer

    def onTick_(self, timer):
        started = self.schedule.tick()
        if started is not None:
            self.announce(started)
        self.render()
        self._ticks += 1
        if self._ticks % SAVE_EVERY == 0:
            self._persist()

    # ---------------------------------------------------------------- display

    @objc.python_method
    def _apply_visibility(self, is_desktop):
        """The widget is always there. The tab only exists while an app covers it."""
        self.widget.set_visible(not self._hidden)
        self.tab.set_visible(not self._hidden and not is_desktop)

    @objc.python_method
    def on_frontmost_change(self, is_desktop):
        self._cancel_collapse()
        self.widget.close()     # you switched away; the controls are done
        self._apply_visibility(is_desktop)
        self.render()

    def screensChanged_(self, note):
        # A display appearing or disappearing means the widget is somewhere new.
        # Leaving its controls hanging open through that is just clutter.
        self.widget.close()
        self.widget.reposition()
        self.tab.relayout()
        self.render()

    @objc.python_method
    def widget_opened(self, opening):
        """The controls only need to be there while you are using them."""
        self._cancel_widget_close()
        if opening:
            self._widget_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                WIDGET_OPEN_FOR, self, "closeWidgetNow:", None, False)
        self.render()

    @objc.python_method
    def _cancel_widget_close(self):
        if self._widget_timer is not None:
            self._widget_timer.invalidate()
            self._widget_timer = None

    def closeWidgetNow_(self, timer):
        self._widget_timer = None
        self.widget.set_open(False)
        self.render()

    @objc.python_method
    def expand(self):
        self.tab.set_expanded(True)
        self.render()
        self._cancel_collapse()
        self._collapse_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            COLLAPSE_AFTER, self, "collapseNow:", None, False)

    @objc.python_method
    def collapse(self):
        self._cancel_collapse()
        self.tab.set_expanded(False)
        self.render()

    @objc.python_method
    def _cancel_collapse(self):
        if self._collapse_timer is not None:
            self._collapse_timer.invalidate()
            self._collapse_timer = None

    def collapseNow_(self, timer):
        self._collapse_timer = None
        self.tab.set_expanded(False)
        self.render()

    # ------------------------------------------------------------ persistence

    @objc.python_method
    def _restore(self):
        """Carry today's totals across a restart, but never across a date."""
        state = config.load_today()
        if state.get("position"):
            self.widget.set_position(state["position"])
        if state.get("date") != dt.date.today().isoformat():
            return
        self.schedule.worked_seconds = float(state.get("worked_seconds", 0.0))
        self.schedule.worked_since_meal = float(state.get("worked_since_meal", 0.0))
        self.schedule.blocks_done = int(state.get("blocks_done", 0))
        self.schedule.set_gear(state.get("gear", self.schedule.gear))

    @objc.python_method
    def _persist(self):
        config.save_today({
            "date": dt.date.today().isoformat(),
            "worked_seconds": round(self.schedule.worked_today(), 1),
            "worked_since_meal": round(self.schedule.worked_since_meal, 1),
            "blocks_done": self.schedule.blocks_done,
            "gear": self.schedule.gear,
            "position": self.widget.position(),
        })

    # --------------------------------------------------------------- announce

    @objc.python_method
    def announce(self, phase):
        """A phase just began on its own. Say so, once."""
        sounds = self.cfg.get("sounds", True)
        banners = self.cfg.get("notifications", True)
        title, body = pet.ANNOUNCEMENTS.get(phase, (None, None))

        if self.schedule.rolled_from_small:
            self.schedule.rolled_from_small = False
            title, body = pet.ROLLED_FROM_SMALL

        shift = self.schedule.last_gear_change
        if shift:
            body = pet.GEAR_NOTES.get(shift, body)
            self.schedule.last_gear_change = None
            config.save_mode(shift)

        if title:
            notify.banner(title, body or "", banners)
        notify.chime(pet.SOUNDS.get(phase, ""), sounds)
        self._persist()

    # ----------------------------------------------------------------- render

    @objc.python_method
    def _readout(self):
        """(big clock text, menu bar text) for the current phase."""
        phase = self.schedule.phase
        glyph = pet.menu_glyph(self.cfg.get("animal", "fox"), phase)
        if phase is Phase.IDLE:
            return "--:--", glyph
        if phase is Phase.MEETING:
            # Counting up, not down: useful to see how long a call has run.
            elapsed = fmt.clock(self.schedule.elapsed_in_phase())
            return elapsed, f"{glyph} {elapsed}"
        if phase in OPEN_ENDED and phase is not Phase.PAUSED:
            return "—", glyph
        countdown = fmt.clock(self.schedule.remaining())
        return countdown, f"{glyph} {countdown}"

    @objc.python_method
    def _headline(self):
        phase = self.schedule.phase
        if phase is Phase.IDLE:
            return "Not started"
        if phase is Phase.MEAL:
            return "Meal — nothing is counting down"
        if phase is Phase.DAY_DONE:
            return "Done for today"
        if phase is Phase.MEETING:
            label = (self.schedule.meeting or {}).get("label", "Meeting")
            return f"{label} · {fmt.clock(self.schedule.elapsed_in_phase())} so far"
        return f"{pet.label(phase).capitalize()} · {fmt.clock(self.schedule.remaining())} left"

    @objc.python_method
    def render(self):
        schedule = self.schedule
        phase = schedule.phase
        primary, secondary = actions.buttons(schedule)
        big, bar_title = self._readout()
        worked = schedule.worked_today()

        status = pet.label(phase)
        if worked >= 60:
            status = f"{status} · {fmt.span(worked)} today"
        elif phase is Phase.IDLE:
            status = "press start"

        animal = self.cfg.get("animal", "fox")
        cycle = sprite.frames(animal, pet.mood(phase))
        rows = cycle[self._ticks % len(cycle)]
        colours = sprite.colours(animal)
        first = primary[0] if primary else ""
        second = secondary[0] if secondary else ""

        self.widget.update(rows, colours, big, status, first, second,
                           schedule.progress())
        self.tab.update(rows, colours, big, status, first, second,
                        pet.menu_glyph(animal, phase))

        upcoming = ""
        if phase not in (Phase.MEAL, Phase.DAY_DONE, Phase.IDLE):
            upcoming = f"Next: {schedule.next_break_label()}"
        self.menubar.update(
            bar_title, self._headline(),
            f"Worked today: {fmt.span(worked)}" if worked >= 60 else "Nothing logged yet",
            upcoming, primary[1] if primary else "",
            secondary[1] if secondary else "",
            schedule.gear, self.cfg.get("adapt_mode", True), not self._hidden)

    # ---------------------------------------------------------------- actions

    @objc.python_method
    def _run(self, method_name):
        getattr(self.schedule, method_name)()
        self.schedule.last_gear_change = None   # a deliberate click needs no note
        if self.tab.is_expanded():
            self.expand()          # clicking something buys another 10 seconds
        if self.widget.is_open():
            self.widget_opened(True)
        self.render()
        self._persist()

    @objc.python_method
    def do_primary(self):
        primary, _ = actions.buttons(self.schedule)
        if primary:
            self._run(primary[2])

    @objc.python_method
    def do_secondary(self):
        _, secondary = actions.buttons(self.schedule)
        if secondary:
            self._run(secondary[2])

    @objc.python_method
    def set_gear(self, gear):
        self.schedule.set_gear(gear)
        config.save_mode(gear)
        self.render()

    @objc.python_method
    def toggle_adapt(self):
        self.cfg["adapt_mode"] = not self.cfg.get("adapt_mode", True)
        self.render()

    @objc.python_method
    def toggle_pet(self):
        self._hidden = not self._hidden
        self._apply_visibility(self.presence.is_desktop())
        self.render()

    @objc.python_method
    def reset_day(self):
        self.schedule.reset_day()
        self.render()
        self._persist()

    @objc.python_method
    def quit(self):
        self._persist()
        NSApplication.sharedApplication().terminate_(None)


# Module level, not an attribute on NSApplication: a bridged ObjC object will
# not hold a Python attribute, and without a reference here the controller is
# collected the moment main() returns into the event loop.
_CONTROLLER = None


def build():
    """Everything main() does except starting the event loop, so it is testable."""
    global _CONTROLLER
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # no dock icon
    _CONTROLLER = AppController.alloc().init()
    _CONTROLLER.startTicking()
    return app, _CONTROLLER


def main():
    build()
    AppHelper.runEventLoop()
