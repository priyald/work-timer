"""Notifications and sounds, shelled out to macOS.

Deliberately using osascript and afplay rather than a notification framework:
both work from a plain unsigned script with no app bundle and no permission
dance, which is the difference between this running today and not.
"""

from __future__ import annotations

import shutil
import subprocess

_OSASCRIPT = shutil.which("osascript")
_AFPLAY = shutil.which("afplay")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def banner(title: str, body: str = "", enabled: bool = True) -> None:
    """Fire and forget. A failed notification must never take the timer down."""
    if not enabled or not _OSASCRIPT:
        return
    script = f'display notification "{_escape(body)}" with title "{_escape(title)}"'
    try:
        subprocess.Popen([_OSASCRIPT, "-e", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def chime(name: str, enabled: bool = True) -> None:
    if not enabled or not _AFPLAY or not name:
        return
    try:
        subprocess.Popen([_AFPLAY, f"/System/Library/Sounds/{name}.aiff"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
