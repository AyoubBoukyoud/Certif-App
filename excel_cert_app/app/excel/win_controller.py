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


def kill_all_excel_processes() -> None:
    """Force-close every EXCEL.EXE process on the machine, including any not
    owned by this controller. In the kiosk exam context this is intentional:
    no unrelated Excel work is expected to be open on the machine, and a
    fresh launch must never inherit a stray process left over from a
    previous crashed or aborted run."""
    import subprocess

    subprocess.run(
        ["taskkill", "/F", "/IM", "EXCEL.EXE", "/T"],
        capture_output=True,
    )


class WinExcelController(ExcelController):
    can_position = True
    can_guard_close = True
    can_toggle_chrome = True

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
            self._wb.Windows(1).WindowState = -4143  # xlNormal, so we can position it
        except Exception:
            pass
        try:
            self._excel.WindowState = -4143  # xlNormal, so we can position it
        except Exception:
            pass

    # -- window positioning ------------------------------------------------

    def _hwnd(self):
        # Excel.Application.Hwnd is the handle of this instance's main window,
        # so we target exactly our process rather than guessing via EnumWindows.
        # Right after Workbooks.Open the property can briefly raise before the
        # new document window is fully registered, so fall back to scanning
        # our own top-level XLMAIN windows rather than giving up.
        try:
            return int(self._excel.Hwnd)
        except Exception:
            pass
        handles = self.excel_window_handles()
        return handles[0] if handles else None

    def position_window(self, x: int, y: int, width: int, height: int) -> None:
        import ctypes
        from ctypes import wintypes

        import win32con
        import win32gui

        hwnd = self._hwnd()
        if not hwnd:
            return
        # A window left in a maximized/minimized state ignores an explicit
        # resize request, so force it back to normal before moving it.
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # DWM wraps top-level windows in an invisible resize border (drop-
        # shadow hit-testing padding) that GetWindowRect includes but that
        # isn't actually visible on screen. A plain MoveWindow(x, y, w, h)
        # therefore leaves the *visible* Excel frame inset from (x, y, w, h)
        # by that padding, i.e. a gap around the window. Measure the padding
        # via DWMWA_EXTENDED_FRAME_BOUNDS (the true visible bounds) against
        # GetWindowRect and inflate the target rect to compensate so the
        # visible frame lands exactly on the requested rect.
        pad_left = pad_top = pad_right = pad_bottom = 0
        try:
            win_rect = win32gui.GetWindowRect(hwnd)
            ext = wintypes.RECT()
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(ext), ctypes.sizeof(ext),
            )
            pad_left = ext.left - win_rect[0]
            pad_top = ext.top - win_rect[1]
            pad_right = win_rect[2] - ext.right
            pad_bottom = win_rect[3] - ext.bottom
        except Exception:
            pass

        win32gui.MoveWindow(
            hwnd,
            x - pad_left, y - pad_top,
            width + pad_left + pad_right, height + pad_top + pad_bottom,
            True,
        )
        win32gui.SetForegroundWindow(hwnd)

    def set_chrome_visible(self, visible: bool) -> None:
        if self._excel is None:
            return
        try:
            self._excel.DisplayFullScreen = not visible
        except Exception:
            pass

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
