"""Which app is in front, so the pet can get out of the way.

On the desktop the pet is a widget. The moment any app takes focus it parks
itself at the screen edge, because covering someone's work is the fastest way
to get an overlay closed forever.

NSWorkspace tells us the frontmost app with no accessibility permission and no
polling. "Desktop" here means Finder is frontmost, which is the best proxy the
public API gives us: it is also true when a Finder window is focused, so you may
occasionally see the widget over a file browser. That is the tolerable error.
"""

from __future__ import annotations

import objc
from AppKit import NSWorkspace
from Foundation import NSObject

DESKTOP_APPS = {"com.apple.finder"}


class Presence(NSObject):
    """Calls on_change(is_desktop) whenever the frontmost app changes."""

    def init(self):
        self = objc.super(Presence, self).init()
        if self is None:
            return None
        self._on_change = None
        self._is_desktop = self._read()
        centre = NSWorkspace.sharedWorkspace().notificationCenter()
        centre.addObserver_selector_name_object_(
            self, "appActivated:", "NSWorkspaceDidActivateApplicationNotification", None)
        return self

    @objc.python_method
    def set_callback(self, on_change):
        self._on_change = on_change

    @objc.python_method
    def _read(self):
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return True
        return app.bundleIdentifier() in DESKTOP_APPS

    @objc.python_method
    def is_desktop(self):
        return self._is_desktop

    def appActivated_(self, note):
        was = self._is_desktop
        self._is_desktop = self._read()
        if self._is_desktop != was and self._on_change:
            self._on_change(self._is_desktop)

    def stop(self):
        NSWorkspace.sharedWorkspace().notificationCenter().removeObserver_(self)
