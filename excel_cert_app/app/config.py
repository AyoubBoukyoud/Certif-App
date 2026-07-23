"""Central configuration: paths, defaults, and runtime constants.

Nothing in here touches Qt or platform APIs, so it is safe to import from
tests and from any layer of the app.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# --- Locations -------------------------------------------------------------

# Repo/package root (…/excel_cert_app).
PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent

CONTENT_DIR: Path = PACKAGE_ROOT / "content"
PROJECTS_DIR: Path = CONTENT_DIR / "projects"
SOLUTIONS_DIR: Path = CONTENT_DIR / "solutions"
TASKS_DIR: Path = CONTENT_DIR / "tasks"


def _user_data_dir() -> Path:
    """Per-user, writable location for the DB, work files and logs."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "ExcelCert"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ExcelCert"
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / "excel-cert"


DATA_DIR: Path = Path(os.environ.get("EXCEL_CERT_DATA_DIR") or _user_data_dir())
DB_PATH: Path = DATA_DIR / "excel_cert.sqlite3"
WORK_DIR: Path = DATA_DIR / "work"
ARCHIVE_DIR: Path = DATA_DIR / "archive"
LOG_DIR: Path = DATA_DIR / "logs"

# --- Exam rules (overridable via the settings table) -----------------------

DEFAULT_EXAM_MINUTES: int = 50
DEFAULT_PASS_THRESHOLD: int = 85          # percent
PROJECTS_PER_EXAM: int = 7

# Variant A -> projects 1..7 ; Variant B -> project 1 + 8..13.
# Project 1 is always included in both variants.
VARIANT_PROJECTS: dict[str, list[int]] = {
    "A": [1, 2, 3, 4, 5, 6, 7],
    "B": [1, 8, 9, 10, 11, 12, 13],
}

# --- UI --------------------------------------------------------------------

APP_NAME: str = "Simulateur de Certification Excel"
ORG_NAME: str = "MOS"
APP_VERSION: str = "1.0.0"  # bumped by hand; surfaced in remote audit_logs rows
# The bottom task panel takes this fraction of the screen height (Excel gets the
# rest). 0.25 -> panel = 1/4 of the screen, Excel = 3/4.
PANEL_HEIGHT_FRACTION: float = 0.25
PANEL_MIN_HEIGHT: int = 260                # px floor for very short screens
PANEL_HEIGHT: int = 260                    # fallback when no screen size is known
# Size of the Excel window itself, as a fraction of the screen's width/height.
# 1.0 x 1.0 -> Excel fills the entire screen. The task panel stays on top of
# it (WindowStaysOnTopHint), so it remains visible even though it now
# overlaps the bottom of the Excel window (sheet-tab strip included).
EXCEL_WIDTH_FRACTION: float = 1.0
EXCEL_HEIGHT_FRACTION: float = 1.0
# Extra vertical room handed to Excel (taken out of the panel's share) so an
# intermittent Excel notification bar (e.g. the "product not activated"
# banner) never pushes the sheet-tab strip below the visible window edge.
EXCEL_HEIGHT_BUFFER_PX: int = 50
LOW_TIME_WARNING_S: int = 300              # clock turns red under 5 minutes


def ensure_runtime_dirs() -> None:
    """Create the writable runtime directories if they do not yet exist."""
    for d in (DATA_DIR, WORK_DIR, ARCHIVE_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def project_workbook(project_no: int) -> Path:
    """Pristine workbook shipped with the app for a given project number."""
    return PROJECTS_DIR / f"MOS_Excel2016_Projet{project_no}.xlsx"


def task_file(project_no: int) -> Path:
    return TASKS_DIR / f"projet{project_no}.xml"
