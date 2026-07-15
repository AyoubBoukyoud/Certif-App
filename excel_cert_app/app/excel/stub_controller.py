"""Development stub controller (non-Windows).

Opens the workbook with the OS default application (e.g. LibreOffice Calc), so
a developer can actually edit and save the file and exercise the grading path.
Window positioning and close-guarding are no-ops here.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .base import ExcelController


class StubExcelController(ExcelController):
    can_position = False
    can_guard_close = False

    def __init__(self, auto_open: bool = True) -> None:
        self._current: Path | None = None
        self._proc: subprocess.Popen | None = None
        self._auto_open = auto_open

    def start(self) -> None:  # nothing to pre-launch
        return

    def _open_cmd(self, path: Path) -> list[str] | None:
        if sys.platform == "darwin":
            return ["open", str(path)]
        if sys.platform.startswith("linux"):
            opener = shutil.which("xdg-open") or shutil.which("libreoffice")
            if opener:
                return [opener, str(path)]
        return None

    def open_project(self, path: Path) -> None:
        self._current = Path(path)
        if not self._auto_open:
            return
        cmd = self._open_cmd(self._current)
        if cmd:
            try:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except OSError:
                self._proc = None

    def position_window(self, x: int, y: int, width: int, height: int) -> None:
        return

    def set_chrome_visible(self, visible: bool) -> None:
        return

    def force_save(self) -> Path | None:
        # The real editor saves in place; here we simply report the path.
        return self._current

    def close_workbook(self, save: bool = True) -> None:
        return

    def shutdown(self) -> None:
        self._current = None

    def is_alive(self) -> bool:
        return True

    def active_workbook_path(self) -> str | None:
        return str(self._current) if self._current else None
