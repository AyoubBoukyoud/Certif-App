"""No-op lock for development / non-Windows platforms.

Fullscreen and always-on-top still apply (handled by the UI), but OS-level key
blocking is unavailable, so this simply records escape attempts if asked.
"""
from __future__ import annotations

from .base import KioskLock


class NoopKioskLock(KioskLock):
    supported = False

    def engage(self) -> None:
        self.engaged = True

    def release(self) -> None:
        self.engaged = False

    def enforce(self, allowed_hwnds: list[int]) -> None:
        return
