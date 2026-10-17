"""Draws a sprite grid as actual pixels.

Scales to whatever rectangle it is given and centres itself, so the same
creature works at 100 points on the desktop widget and at 49 in the compact
card without a second set of art.
"""

from __future__ import annotations

import objc
from AppKit import NSBezierPath, NSColor, NSRectFill, NSView
from Foundation import NSMakeRect

# Half a point of overdraw, so neighbouring pixels never show a hairline seam
# at fractional cell sizes.
BLEED = 0.5


class PixelView(NSView):

    def init(self):
        self = objc.super(PixelView, self).init()
        if self is None:
            return None
        self._rows = []
        self._palette = {}
        return self

    @objc.python_method
    def set_grid(self, rows, palette):
        if rows == self._rows and palette == self._palette:
            return
        self._rows = rows
        self._palette = palette
        self.setNeedsDisplay_(True)

    def isOpaque(self):
        return False

    def hitTest_(self, point):
        return None     # clicks belong to whatever is behind the artwork

    def drawRect_(self, dirty):
        rows = self._rows
        if not rows:
            return
        bounds = self.bounds()
        columns, count = len(rows[0]), len(rows)
        cell = min(bounds.size.width / columns, bounds.size.height / count)
        left = (bounds.size.width - cell * columns) / 2.0
        bottom = (bounds.size.height - cell * count) / 2.0

        for index, row in enumerate(rows):
            y = bottom + (count - 1 - index) * cell     # grids read top down
            for column, char in enumerate(row):
                colour = self._palette.get(char)
                if colour is None:
                    continue
                NSColor.colorWithSRGBRed_green_blue_alpha_(*colour).set()
                NSRectFill(NSMakeRect(left + column * cell, y,
                                      cell + BLEED, cell + BLEED))


class SolidView(NSView):
    """A rounded block of one colour.

    Drawn rather than set as a layer background: reaching for CGColor without
    the Quartz bindings installed produces an opaque pointer and a warning on
    every launch, and this is less machinery than fixing that.
    """

    def init(self):
        self = objc.super(SolidView, self).init()
        if self is None:
            return None
        self._colour = None
        return self

    @objc.python_method
    def set_colour(self, colour):
        self._colour = colour

    def isOpaque(self):
        return False

    def hitTest_(self, point):
        return None

    def drawRect_(self, dirty):
        if self._colour is None:
            return
        bounds = self.bounds()
        radius = min(bounds.size.height / 2.0, bounds.size.width / 2.0)
        self._colour.set()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, radius, radius).fill()
