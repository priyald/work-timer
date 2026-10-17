"""The edge tab: how you reach the timer from inside an app.

The desktop widget is behind your windows, so while you are working it is
covered. This is the part that stays reachable: a sliver parked at the right
edge, mostly off screen, floating above app windows but only 15 points wide so
it covers nothing you are reading. Click it and a compact card slides out for a
few seconds.

It is a separate window from the widget on purpose. Making one panel do both
jobs meant the widget had to move out of place every time you switched apps,
which is the opposite of a widget.
"""

from __future__ import annotations

import objc
from AppKit import NSColor, NSControlSizeMini, NSFont, NSScreen
from Foundation import NSMakeRect, NSObject

from . import panels
from .levels import STATUS
from .pixelview import PixelView

CARD_W, CARD_H = 218.0, 126.0
TAB_W, TAB_H = 34.0, 74.0
TAB_PEEK = 15.0        # how much of the tab stays on screen
EDGE_GAP = 8.0
HEIGHT_FRACTION = 0.55  # how far up the screen it sits


class EdgeTab(NSObject):

    def init(self):
        self = objc.super(EdgeTab, self).init()
        if self is None:
            return None
        self._handlers = {}
        self._expanded = False
        self._build()
        return self

    @objc.python_method
    def set_handlers(self, handlers):
        self._handlers = handlers

    # ------------------------------------------------------------------ build

    def _build(self):
        window = panels.panel(CARD_W, CARD_H, STATUS, draggable=False)
        face = panels.skin(window, CARD_W, CARD_H, 15.0)

        self._pet = PixelView.alloc().init()
        self._pet.setFrame_(NSMakeRect(0, 76, CARD_W, 46))
        self._clock = panels.label(NSMakeRect(0, 46, CARD_W, 30), 23.0,
                                   NSColor.labelColor(), mono=True)
        self._status = panels.label(NSMakeRect(0, 32, CARD_W, 13), 10.0,
                                    NSColor.secondaryLabelColor())
        self._primary = panels.button("Start", NSMakeRect(14, 6, 112, 24),
                                      self, "primaryClicked:")
        self._secondary = panels.button("", NSMakeRect(132, 6, 72, 24),
                                        self, "secondaryClicked:")
        self._collapse = panels.button("»", NSMakeRect(6, CARD_H - 22, 24, 16),
                                       self, "collapseClicked:", NSControlSizeMini)
        self._collapse.setBordered_(False)
        self._restart = panels.button("↺", NSMakeRect(CARD_W - 31, CARD_H - 22, 24, 16),
                                      self, "restartClicked:", NSControlSizeMini)
        self._restart.setBordered_(False)

        # One big invisible button: at 15 points wide, a small hit area would be
        # unusable, so the whole sliver is the target.
        self._tab = panels.button("", NSMakeRect(0, 0, TAB_W, TAB_H),
                                  self, "tabClicked:")
        self._tab.setBordered_(False)
        self._tab.setFont_(NSFont.systemFontOfSize_(15.0))

        self._card = (self._pet, self._clock, self._status, self._primary,
                      self._secondary, self._collapse, self._restart)
        for view in self._card + (self._tab,):
            face.addSubview_(view)

        self._window = window
        self._layout()
        window.orderOut_(None)     # only shown once you are inside an app

    # ----------------------------------------------------------------- layout

    @objc.python_method
    def _layout(self):
        for view in self._card:
            view.setHidden_(not self._expanded)
        self._tab.setHidden_(self._expanded)

        screen = NSScreen.mainScreen()
        if screen is None:
            return
        area = screen.visibleFrame()
        right = area.origin.x + area.size.width
        anchor = area.origin.y + area.size.height * HEIGHT_FRACTION

        if self._expanded:
            rect = NSMakeRect(right - CARD_W - EDGE_GAP,
                              anchor - (CARD_H - TAB_H) / 2.0, CARD_W, CARD_H)
        else:
            rect = NSMakeRect(right - TAB_PEEK, anchor, TAB_W, TAB_H)
        self._window.setFrame_display_(rect, True)

    @objc.python_method
    def relayout(self):
        """Screens changed; the right edge is somewhere else now."""
        self._layout()

    @objc.python_method
    def set_expanded(self, expanded):
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self._layout()

    @objc.python_method
    def is_expanded(self):
        return self._expanded

    # ----------------------------------------------------------------- render

    @objc.python_method
    def update(self, pet_rows, pet_colours, clock, status, primary, secondary,
               tab_glyph=""):
        self._tab.setTitle_(tab_glyph)
        if not self._expanded:
            return                      # nothing else is on screen to update
        self._pet.set_grid(pet_rows, pet_colours)
        self._clock.setStringValue_(clock)
        self._status.setStringValue_(status)
        self._primary.setTitle_(primary or "")
        self._primary.setHidden_(not primary)
        self._secondary.setTitle_(secondary or "")
        self._secondary.setHidden_(not secondary)

    @objc.python_method
    def set_visible(self, visible):
        if visible:
            self._window.orderFrontRegardless()
        else:
            self.set_expanded(False)
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

    def collapseClicked_(self, sender):
        self._handlers["collapse"]()

    def tabClicked_(self, sender):
        self._handlers["expand"]()
