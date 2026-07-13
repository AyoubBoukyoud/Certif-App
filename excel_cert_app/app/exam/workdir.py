"""Per-session working copies of the project workbooks.

The candidate never edits the pristine content files; each exam gets its own
copy under ``DATA_DIR/work/{session_id}/``. Auxiliary data files needed by
some tasks (e.g. Donateurs.txt for import tasks) are copied alongside.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from .. import config


def session_dir(session_id: int) -> Path:
    return config.WORK_DIR / str(session_id)


def workfile_path(session_id: int, project_no: int) -> Path:
    return session_dir(session_id) / f"P{project_no}.xlsx"


def prepare_project(session_id: int, project_no: int) -> Path:
    """Copy the pristine workbook (and any sibling data files) into the work dir."""
    sdir = session_dir(session_id)
    sdir.mkdir(parents=True, exist_ok=True)

    src = config.project_workbook(project_no)
    dst = workfile_path(session_id, project_no)
    if not dst.exists():
        shutil.copy2(src, dst)

    # Copy any auxiliary data files shipped next to the pristine workbook
    # (import tasks reference e.g. Donateurs.txt / Boissons.txt).
    for aux in config.PROJECTS_DIR.glob("*.txt"):
        target = sdir / aux.name
        if not target.exists():
            shutil.copy2(aux, target)

    return dst


def archive_session(session_id: int) -> Path | None:
    """Zip the work dir into the archive folder for audit, then remove it."""
    sdir = session_dir(session_id)
    if not sdir.exists():
        return None
    config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive = config.ARCHIVE_DIR / f"session_{session_id}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sdir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(sdir))
    shutil.rmtree(sdir, ignore_errors=True)
    return archive
