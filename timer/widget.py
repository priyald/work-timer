"""The desktop widget. Fixed in place, and it stays there.

Collapsed it shows one thing: the timer. Click it and the controls open, the way
clicking a widget opens its app. Click again, or leave it, and it goes back to
being just a timer.

It sits behind every app window and above the desktop and its folders, and
unlike a true desktop-level window it still takes clicks — see levels.py for why
that rules the desktop level out. Switching to an app does not move it; your
windows simply cover it. Reaching the timer from inside an app is the edge tab's
job, not this one's.

Drag it wherever you want. The position is remembered per display.
"""

from __future__ import annotations

import objc
from AppKit import NSColor, NSScreen
from Foundation import NSMakeRect, NSMakePoint, NSObject

from . import panels
from .levels import WIDGET as WIDGET_LEVEL
from .pixelview import PixelView

WIDTH = 240.0
SHUT = 186.0            # just the timer
OPEN = 226.0            # with the control row
CONTROLS = OPEN - SHUT

MARGIN = 40.0
BAR_INSET, BAR_HEIGHT = 26.0, 5.0


class DesktopWidget(NSObject):

    def init(self):
        self = objc.super(DesktopWidget, self).init()
        if self is None:
            return None
        self._handlers = {}
        self._position = None
        self._open = False
        self._build()
        return self

    @objc.python_method
    def set_handlers(self, handlers):
        """Set after construction: a dict passed through an ObjC selector would
        be bridged to an NSDictionary and lose the Python callables inside."""
        self._handlers = handlers

    # ------------------------------------------------------------------ build

    def _build(self):
        window = panels.panel(WIDTH, OPEN, WIDGET_LEVEL, draggable=False)
        face = panels.skin(window, WIDTH, OPEN, 22.0)

        # Added first, so it sits behind everything and catches what the
        # artwork and labels let through.
        self._background = panels.DragClickView.alloc().init()
        self._background.setFrame_(NSMakeRect(0, 0, WIDTH, OPEN))
        self._background.set_on_click(self.toggle)
        self._background.set_on_drag(self.close)
        face.addSubview_(self._background)

        self._pet = PixelView.alloc().init()
        self._clock = panels.label(NSMakeRect(0, 0, 1, 1), 34.0,
                                   NSColor.labelColor(), mono=True)
        self._status = panels.label(NSMakeRect(0, 0, 1, 1), 11.0,
                                    NSColor.secondaryLabelColor())
        self._track = panels.bar(NSMakeRect(0, 0, 1, BAR_HEIGHT),
                                 NSColor.separatorColor())
        self._fill = panels.bar(NSMakeRect(0, 0, 1, BAR_HEIGHT),
                                NSColor.controlAccentColor())

        self._restart = panels.button("↺", NSMakeRect(14, 8, 40, 28),
                                      self, "restartClicked:")
        self._primary = panels.button("Start", NSMakeRect(60, 8, 106, 28),
                                      self, "primaryClicked:")
        self._secondary = panels.button("", NSMakeRect(172, 8, 54, 28),
                                        self, "secondaryClicked:")
        self._controls = (self._restart, self._primary, self._secondary)

        for view in (self._pet, self._clock, self._status, self._track,
                     self._fill) + self._controls:
            face.addSubview_(view)

        self._window = window
        self._relayout()
        self._apply()
        window.orderBack_(None)     # behind everything, but still clickable

    # ----------------------------------------------------------------- layout

    @objc.python_method
    def _height(self):
        return OPEN if self._open else SHUT

    @objc.python_method
    def _relayout(self):
        """Lay the timer out against the current height, with the control row
        below it when open."""
        height = self._height()
        lift = CONTROLS if self._open else 0.0
        self._pet.setFrame_(NSMakeRect(0, height - 102, WIDTH, 94))
        self._clock.setFrame_(NSMakeRect(0, 42 + lift, WIDTH, 42))
        self._status.setFrame_(NSMakeRect(0, 24 + lift, WIDTH, 16))
        track = NSMakeRect(BAR_INSET, 14 + lift, WIDTH - BAR_INSET * 2, BAR_HEIGHT)
        self._track.setFrame_(track)
        self._track_rect = track
        self._background.setFrame_(NSMakeRect(0, 0, WIDTH, height))
        for control in self._controls:
            control.setHidden_(not self._open)

    @objc.python_method
    def toggle(self):
        self.set_open(not self._open)

    @objc.python_method
    def close(self):
        self.set_open(False)

    @objc.python_method
    def set_open(self, opening):
        if opening == self._open:
            return
        self._open = opening
        self._relayout()
        self._apply()
        if self._handlers.get("opened"):
            self._handlers["opened"](opening)

    @objc.python_method
    def is_open(self):
        return self._open

    # --------------------------------------------------------------- position

    @objc.python_method
    def _display_id(self, screen):
        try:
            return int(screen.deviceDescription()["NSScreenNumber"])
        except (KeyError, TypeError, ValueError):
            return 0

    @objc.python_method
    def _screen_for(self, display):
        for screen in NSScreen.screens():
            if self._display_id(screen) == display:
                return screen
        return NSScreen.mainScreen()

    @objc.python_method
    def _default_position(self):
        """Bottom right. The top right is where macOS puts its own widgets, and
        landing on top of those is exactly what we are avoiding."""
        screen = NSScreen.mainScreen()
        if screen is None:
            return None
        area = screen.visibleFrame()
        return {"display": self._display_id(screen),
                "dx": float(area.size.width - WIDTH - MARGIN),
                "dy": MARGIN}

    @objc.python_method
    def position(self):
        """Where it sits, as an offset inside one named display.

        Stored this way rather than as absolute screen coordinates because those
        only mean anything for one particular monitor arrangement: plug a second
        display in, or unplug one, and yesterday's coordinates point somewhere
        else. Always reported as the collapsed position, so opening the controls
        does not slowly walk the widget down the screen.
        """
        screen = self._window.screen() or NSScreen.mainScreen()
        if screen is None:
            return self._position
        area = screen.visibleFrame()
        frame = self._window.frame()
        self._position = {
            "display": self._display_id(screen),
            "dx": float(frame.origin.x - area.origin.x),
            "dy": float(frame.origin.y - area.origin.y) + (CONTROLS if self._open else 0.0),
        }
        return self._position

    @objc.python_method
    def set_position(self, position):
        if not isinstance(position, dict):
            return                      # an older absolute position; ignore it
        self._position = position
        self._apply()

    @objc.python_method
    def _apply(self):
        """Place the window, keeping its top edge fixed as it opens and closes."""
        position = self._position or self._default_position()
        if position is None:
            return
        screen = self._screen_for(position.get("display", 0))
        if screen is None:
            return
        area = screen.visibleFrame()
        height = self._height()
        x = area.origin.x + float(position.get("dx", 0.0))
        y = area.origin.y + float(position.get("dy", 0.0)) - (height - SHUT)
        # Clamp onto that display, in case it is now a smaller one.
        x = min(max(x, area.origin.x), area.origin.x + area.size.width - WIDTH)
        y = min(max(y, area.origin.y), area.origin.y + area.size.height - height)
        self._window.setFrame_display_(NSMakeRect(x, y, WIDTH, height), True)

    @objc.python_method
    def reposition(self):
        """The screen arrangement changed. Put it back on its own display."""
        self._apply()

    # ----------------------------------------------------------------- render

    @objc.python_method
    def update(self, pet_rows, pet_colours, clock, status, primary, secondary,
               progress=None):
        self._pet.set_grid(pet_rows, pet_colours)
        self._clock.setStringValue_(clock)
        self._status.setStringValue_(status)
        self._primary.setTitle_(primary or "")
        self._primary.setEnabled_(bool(primary))
        self._secondary.setTitle_(secondary or "")
        self._secondary.setEnabled_(bool(secondary))

        showing = progress is not None
        self._track.setHidden_(not showing)
        self._fill.setHidden_(not showing)
        if showing:
            width = max(0.0, min(1.0, progress)) * self._track_rect.size.width
            self._fill.setFrame_(NSMakeRect(
                self._track_rect.origin.x, self._track_rect.origin.y,
                width, BAR_HEIGHT))

    @objc.python_method
    def set_visible(self, visible):
        if visible:
            self._window.orderBack_(None)
        else:
            self._window.orderOut_(None)

    @objc.python_method
    def is_visible(self):
        return bool(self._window.isVisible())

    # ---------------------------------------------------------------- actions

    def primaryClicked_(self, sender):
        self._handlers["primary"]()

    def secondaryClicked_(self, sender):
        self._handlers["secondary"]()

    def restartClicked_(self, sender):
        self._handlers["restart"]()
