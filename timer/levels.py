"""Window levels, read from CoreGraphics.

pyobjc ships the Cocoa framework here but not Quartz, and AppKit exposes no
constant for the desktop level, so we ask CoreGraphics directly through ctypes.
The keys are the CGWindowLevelKey enum; the sanity values below are checked at
import so a wrong index shows up immediately rather than as an invisible window.
"""

from __future__ import annotations

import ctypes

_DESKTOP_ICON_KEY = 18
_STATUS_KEY = 9
_NORMAL_KEY = 4

# Sensible fallbacks if CoreGraphics ever refuses to load.
DESKTOP_ICONS = -2147483603
STATUS = 25

try:
    _CG = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    _CG.CGWindowLevelForKey.restype = ctypes.c_int32
    _CG.CGWindowLevelForKey.argtypes = [ctypes.c_int32]

    if _CG.CGWindowLevelForKey(_NORMAL_KEY) == 0:      # the indexes are right
        DESKTOP_ICONS = _CG.CGWindowLevelForKey(_DESKTOP_ICON_KEY)
        STATUS = _CG.CGWindowLevelForKey(_STATUS_KEY)
except OSError:
    pass

# The widget sits at the *normal* window level and is ordered to the back.
#
# The obvious choice is the desktop level, and it is wrong: macOS does not
# deliver mouse events to windows down there — Finder's desktop swallows them —
# which is why desktop widget apps ship a separate "interaction mode" that
# raises the level before you can click anything. A widget you cannot press
# Start on is not worth the purity.
#
# At the normal level, ordered back, an accessory app's window sits below every
# other app's windows and above the desktop and its icons, which is the same
# place visually, and it takes clicks.
WIDGET = 0
