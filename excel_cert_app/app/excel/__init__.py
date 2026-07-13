"""Excel controller factory."""
from __future__ import annotations

import sys

from .base import ExcelController


def create_controller(auto_open: bool = True) -> ExcelController:
    """Return the best controller for this platform.

    Windows with pywin32 available -> real Excel via COM.
    Anything else -> development stub (opens with the default spreadsheet app).
    """
    if sys.platform == "win32":
        try:
            import win32com.client  # noqa: F401

            from .win_controller import WinExcelController

            return WinExcelController()
        except ImportError:
            pass
    from .stub_controller import StubExcelController

    return StubExcelController(auto_open=auto_open)
