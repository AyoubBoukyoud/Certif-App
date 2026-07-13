"""Windows COM controller driving the real Microsoft Excel.

Runs a dedicated Excel instance (never the user's own), positions its window
above the task panel, saves on demand, and exposes hooks the watchdog uses to
keep the candidate inside the exam workbook. Import of pywin32 is deferred so
this module can at least be imported on non-Windows machines.
"""
from __future__ import annotations

import time
from pathlib import Path

from .base import ExcelController

_XLMAIN = "XLMAIN"


class WinExcelController(ExcelController):
    can_position = True
    can_guard_close = True

    def __init__(self) -> None:
        self._excel = None          # Excel.Application COM object
        self._wb = None             # active Workbook
        self._pywintypes = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        import pythoncom
        import win32com.client as win32
        import pywintypes

        pythoncom.CoInitialize()
        self._pywintypes = pywintypes
        # DispatchEx => a brand-new, isolated Excel process (not the user's).
        self._excel = win32.DispatchEx("Excel.Application")
        self._excel.Visible = True
        self._excel.DisplayAlerts = False
        self._excel.AskToUpdateLinks = False
        try:
            self._excel.DisplayFullScreen = False
        except Exception:
            pass

    def open_project(self, path: Path) -> None:
        self.close_workbook(save=True)
        self._wb = self._excel.Workbooks.Open(str(Path(path).resolve()))
        self._excel.Visible = True
        try:
            self._excel.WindowState = -4143  # xlNormal, so we can position it
        except Exception:
            pass

    # -- window positioning ------------------------------------------------

    def _hwnd(self):
        # Excel.Application.Hwnd is the handle of this instance's main window,
        # so we target exactly our process rather than guessing via EnumWindows.
        try:
            return int(self._excel.Hwnd)
        except Exception:
            return None

    def position_window(self, x: int, y: int, width: int, height: int) -> None:
        import win32gui

        hwnd = self._hwnd()
        if hwnd:
            win32gui.MoveWindow(hwnd, x, y, width, height, True)

    # -- save / close ------------------------------------------------------

    def force_save(self) -> Path | None:
        if self._wb is None:
            return None
        path = self._wb.FullName
        self._wb.Save()
        # Give Excel a beat to flush to disk.
        time.sleep(0.2)
        return Path(path)

    def close_workbook(self, save: bool = True) -> None:
        if self._wb is not None:
            try:
                self._wb.Close(SaveChanges=save)
            except Exception:
                pass
            self._wb = None

    def shutdown(self) -> None:
        try:
            self.close_workbook(save=True)
            if self._excel is not None:
                self._excel.Quit()
        except Exception:
            pass
        finally:
            self._excel = None
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except Exception:
                pass

    # -- introspection -----------------------------------------------------

    def is_alive(self) -> bool:
        if self._excel is None:
            return False
        try:
            _ = self._excel.Visible
            return True
        except Exception:
            return False

    def active_workbook_path(self) -> str | None:
        try:
            if self._excel is not None and self._excel.ActiveWorkbook is not None:
                return self._excel.ActiveWorkbook.FullName
        except Exception:
            return None
        return None

    def excel_window_handles(self) -> list[int]:
        """All top-level Excel window handles (used by the focus watchdog)."""
        import win32gui

        handles: list[int] = []

        def _cb(hwnd, _):
            if win32gui.GetClassName(hwnd) == _XLMAIN:
                handles.append(hwnd)
            return True

        win32gui.EnumWindows(_cb, None)
        return handles
