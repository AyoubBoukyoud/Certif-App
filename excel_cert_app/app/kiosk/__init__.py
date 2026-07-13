"""Kiosk lock factory."""
from __future__ import annotations

import sys

from .base import KioskLock


def create_lock() -> KioskLock:
    if sys.platform == "win32":
        try:
            from .win_lock import WinKioskLock

            return WinKioskLock()
        except Exception:
            pass
    from .noop_lock import NoopKioskLock

    return NoopKioskLock()
