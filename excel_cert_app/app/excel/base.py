"""Excel control abstraction.

The exam runs inside the *real* Microsoft Excel. On Windows that is driven
through COM automation; on other platforms (development machines) a stub opens
the workbook in whatever spreadsheet app is available so the rest of the app
can be built and tested end to end.
"""
from __future__ import annotations

import abc
from pathlib import Path


class ExcelController(abc.ABC):
    """Manages one dedicated spreadsheet application instance."""

    @abc.abstractmethod
    def start(self) -> None:
        """Launch the (dedicated) spreadsheet application."""

    @abc.abstractmethod
    def open_project(self, path: Path) -> None:
        """Open a workbook, closing any previously open one."""

    @abc.abstractmethod
    def position_window(self, x: int, y: int, width: int, height: int) -> None:
        """Place the application window in the given screen rectangle."""

    @abc.abstractmethod
    def force_save(self) -> Path | None:
        """Save the active workbook in place; return its path."""

    @abc.abstractmethod
    def close_workbook(self, save: bool = True) -> None:
        """Close the active workbook (optionally saving first)."""

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Quit the application and release resources."""

    @abc.abstractmethod
    def is_alive(self) -> bool:
        """True while the managed application is running and reachable."""

    @abc.abstractmethod
    def active_workbook_path(self) -> str | None:
        """Path of the currently active workbook, or None."""

    # Optional capability flags used by the watchdog/kiosk layer.
    can_position: bool = False
    can_guard_close: bool = False
