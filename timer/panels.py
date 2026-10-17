"""Shared AppKit plumbing for the two panels.

The desktop widget and the edge tab are separate windows living at different
window levels, but they are built the same way: borderless, non-activating (so
clicking never steals focus), on every Space, with a blurred rounded skin.
"""

from __future__ import annotations

from .pixelview import SolidView

import objc
from AppKit import (NSBackingStoreBuffered, NSBezelStyleRounded, NSButton,
                    NSColor, NSControlSizeSmall, NSFont, NSFontWeightMedium,
                    NSPanel, NSTextAlignmentCenter, NSTextField, NSView, NSView,
                    NSVisualEffectBlendingModeBehindWindow,
                    NSVisualEffectMaterialPopover, NSVisualEffectStateActive,
                    NSVisualEffectView,
                    NSWindowCollectionBehaviorCanJoinAllSpaces,
                    NSWindowCollectionBehaviorFullScreenAuxiliary,
                    NSWindowCollectionBehaviorStationary,
                    NSWindowStyleMaskBorderless,
                    NSWindowStyleMaskNonactivatingPanel)
from Foundation import NSMakeRect


class FixedPanel(NSPanel):
    """A panel that stays exactly where it is put.

    AppKit constrains window frames to the screen, which on a dual monitor setup
    means a display being added, removed or rearranged quietly shunts the window
    somewhere else. We choose the position ourselves, so we decline.
    """

    def constrainFrameRect_toScreen_(self, rect, screen):
        return rect


def panel(width, height, level, draggable=True):
    mask = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
    window = FixedPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0.0, 0.0, width, height), mask, NSBackingStoreBuffered, False)
    window.setLevel_(level)
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.clearColor())
    window.setHasShadow_(True)
    window.setHidesOnDeactivate_(False)
    window.setMovableByWindowBackground_(draggable)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorStationary
        | NSWindowCollectionBehaviorFullScreenAuxiliary)
    return window


def skin(window, width, height, radius):
    view = NSVisualEffectView.alloc().initWithFrame_(
        NSMakeRect(0.0, 0.0, width, height))
    view.setMaterial_(NSVisualEffectMaterialPopover)
    view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
    view.setState_(NSVisualEffectStateActive)
    view.setWantsLayer_(True)
    view.layer().setCornerRadius_(radius)
    view.layer().setMasksToBounds_(True)
    window.setContentView_(view)
    return view


def label(rect, size, colour, mono=False):
    field = PassthroughLabel.labelWithString_("")
    field.setFrame_(rect)
    field.setAlignment_(NSTextAlignmentCenter)
    field.setFont_(NSFont.monospacedDigitSystemFontOfSize_weight_(size, NSFontWeightMedium)
                   if mono else NSFont.systemFontOfSize_(size))
    field.setTextColor_(colour)
    return field


def button(title, rect, target, action, size=NSControlSizeSmall, points=11.0):
    control = NSButton.buttonWithTitle_target_action_(title, target, action)
    control.setFrame_(rect)
    control.setBezelStyle_(NSBezelStyleRounded)
    control.setControlSize_(size)
    control.setFont_(NSFont.systemFontOfSize_(points))
    return control


def bar(rect, colour):
    view = SolidView.alloc().init()
    view.setFrame_(rect)
    view.set_colour(colour)
    return view


class PassthroughLabel(NSTextField):
    """A label that is not a click target.

    Without this, text sitting on the widget swallows the click that is supposed
    to reach the background behind it, and half the surface stops responding.
    """

    def hitTest_(self, point):
        return None


class DragClickView(NSView):
    """The widget's background: drag it to move, click it to open the controls.

    Both gestures start the same way, so they are told apart by whether the
    mouse actually moved. A plain movable-by-background window cannot do this,
    because it consumes the click before anything can decide it was a click.
    """

    def init(self):
        self = objc.super(DragClickView, self).init()
        if self is None:
            return None
        self._on_click = None
        self._on_drag = None
        self._dragged = False
        return self

    @objc.python_method
    def set_on_click(self, handler):
        self._on_click = handler

    @objc.python_method
    def set_on_drag(self, handler):
        """Called once a drag finishes, so the window can react to being moved."""
        self._on_drag = handler

    def acceptsFirstMouse_(self, event):
        return True     # respond on the first click, without activating the app

    def mouseDown_(self, event):
        self._dragged = False

    def mouseDragged_(self, event):
        self._dragged = True
        self.window().performWindowDragWithEvent_(event)

    def mouseUp_(self, event):
        if self._dragged:
            if self._on_drag:
                self._on_drag()
        elif self._on_click:
            self._on_click()
