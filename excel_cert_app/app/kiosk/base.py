"""Kiosk lock-down abstraction.

``engage`` installs OS-level restrictions (key hooks); ``enforce`` is called on
a timer to keep focus inside the exam; ``release`` reverses everything. The
fullscreen/always-on-top behaviour of the Qt windows is handled separately by
the UI layer — this class deals only with OS-level lock-down.
"""
from __future__ import annotations

import abc
from typing import Callable


class KioskLock(abc.ABC):
    def __init__(self) -> None:
        self.on_escape: Callable[[str], None] | None = None
        self.engaged = False

    @abc.abstractmethod
    def engage(self) -> None:
        ...

    @abc.abstractmethod
    def release(self) -> None:
        ...

    def enforce(self, allowed_hwnds: list[int]) -> None:
        """Called periodically; refocus the exam if something else grabbed it."""

    supported: bool = False
