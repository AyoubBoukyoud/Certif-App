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


def kill_all_excel_processes() -> None:
    """Force-close every EXCEL.EXE process on the machine (Windows only;
    no-op elsewhere), so a fresh Excel launch never inherits a stray
    process left over from a previous crashed or aborted run."""
    if sys.platform == "win32":
        from .win_controller import kill_all_excel_processes as _kill

        _kill()
