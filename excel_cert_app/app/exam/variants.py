"""Variant selection.

Variant A = projects 1-7, Variant B = project 1 + projects 8-13. Project 1 is
always included. By default variants alternate across candidates so a room of
people sitting side by side don't all get the same exam.
"""
from __future__ import annotations

from .. import config
from ..db.dao import Database


def project_list(variant: str) -> list[int]:
    return list(config.VARIANT_PROJECTS[variant])


def next_variant(db: Database) -> str:
    """Pick the variant, honouring an admin override or alternating otherwise."""
    forced = db.get_setting("variant_mode", "alternate")
    if forced in ("A", "B"):
        return forced
    row = db.conn.execute(
        "SELECT variant FROM sessions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last = row["variant"] if row else None
    return "B" if last == "A" else "A"
