"""The menu bar item: a glanceable countdown plus every control the pet hides.

The pet has room for two buttons. Everything else -- changing gear, hiding the
pet while screen sharing, resetting the day -- lives here.
"""

from __future__ import annotations

import objc
from AppKit import (NSFont, NSMenu, NSMenuItem, NSStatusBar,
                    NSVariableStatusItemLength)
from Foundation import NSObject

from .config import GEAR_ORDER

OFF = 0
ON = 1


class MenuBar(NSObject):
    def init(self):
        self = objc.super(MenuBar, self).init()
        if self is None:
            return None
        self._handlers = {}
        self._build()
        return self

    @objc.python_method
    def set_handlers(self, handlers):
        """Set after construction: passing a dict through an ObjC selector would
        bridge it to an NSDictionary and lose the Python callables inside."""
        self._handlers = handlers

    # ------------------------------------------------------------------ build

    @objc.python_method
    def _item(self, title, action=None, target=None):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, action or "", "")
        if action:
            item.setTarget_(target or self)
        else:
            item.setEnabled_(False)
        return item

    def _build(self):
        bar = NSStatusBar.systemStatusBar()
        self._status = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self._status.button().setFont_(NSFont.monospacedDigitSystemFontOfSize_weight_(12.0, 0.0))

        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)

        self._headline = self._item("Not started")
        self._today = self._item("Nothing logged yet")
        self._upcoming = self._item("")
        for row in (self._headline, self._today, self._upcoming):
            menu.addItem_(row)
        menu.addItem_(NSMenuItem.separatorItem())

        self._primary = self._item("Start working", "primaryClicked:")
        self._secondary = self._item("Break now", "secondaryClicked:")
        menu.addItem_(self._primary)
        menu.addItem_(self._secondary)
        menu.addItem_(NSMenuItem.separatorItem())

        gear_menu = NSMenu.alloc().init()
        gear_menu.setAutoenablesItems_(False)
        self._gear_items = {}
        for gear in GEAR_ORDER:
            entry = self._item(gear.capitalize(), "gearChosen:")
            entry.setRepresentedObject_(gear)
            gear_menu.addItem_(entry)
            self._gear_items[gear] = entry
        gear_menu.addItem_(NSMenuItem.separatorItem())
        self._adapt = self._item("Adapt to how I'm working", "toggleAdapt:")
        gear_menu.addItem_(self._adapt)

        gear_root = self._item("Pace")
        gear_root.setEnabled_(True)
        gear_root.setSubmenu_(gear_menu)
        menu.addItem_(gear_root)

        self._pet_toggle = self._item("Hide the pet", "togglePet:")
        menu.addItem_(self._pet_toggle)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItem_(self._item("Reset today", "resetDay:"))
        menu.addItem_(self._item("Quit", "quitApp:"))

        self._status.setMenu_(menu)

    # ----------------------------------------------------------------- render

    @objc.python_method
    def update(self, title, headline, today, upcoming, primary, secondary,
               gear, adapt, pet_visible):
        self._status.button().setTitle_(title)
        self._headline.setTitle_(headline)
        self._today.setTitle_(today)
        self._upcoming.setTitle_(upcoming)

        self._primary.setTitle_(primary or "")
        self._primary.setHidden_(not primary)
        self._secondary.setTitle_(secondary or "")
        self._secondary.setHidden_(not secondary)

        for name, item in self._gear_items.items():
            item.setState_(ON if name == gear else OFF)
        self._adapt.setState_(ON if adapt else OFF)
        self._pet_toggle.setTitle_("Hide the pet" if pet_visible else "Show the pet")

    # ---------------------------------------------------------------- actions

    def primaryClicked_(self, sender):
        self._handlers["primary"]()

    def secondaryClicked_(self, sender):
        self._handlers["secondary"]()

    def gearChosen_(self, sender):
        self._handlers["gear"](sender.representedObject())

    def toggleAdapt_(self, sender):
        self._handlers["adapt"]()

    def togglePet_(self, sender):
        self._handlers["pet"]()

    def resetDay_(self, sender):
        self._handlers["reset"]()

    def quitApp_(self, sender):
        self._handlers["quit"]()
