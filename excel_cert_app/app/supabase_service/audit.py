"""Mirrors selected local audit events (see `Database.audit` in
`app/db/dao.py`) into the remote `audit_logs` table, via the `log_kiosk_event`
RPC (see ../../../supabase/migrations/0002_kiosk_public_rpc.sql) — the kiosk
holds no établissement/actor session for most of these events (system_check,
excel_crash, escape_attempt can all fire before any candidate is found), so a
direct table insert would be rejected by RLS.

Best-effort and non-blocking: `Database.audit()` (SQLite) stays the source
of truth the app can always write to; a failure here is swallowed and
reported back into that same local log via `local_db`, rather than raised —
losing connectivity must never stop the exam flow.
"""
from __future__ import annotations

import platform

from supabase import Client

from .. import config
from ..db.dao import Database


def log(
    client: Client,
    local_db: Database,
    event: str,
    *,
    candidate_id: str | None = None,
    etablissement_id: str | None = None,
    result: str = "ok",
    message: str = "",
) -> None:
    try:
        client.rpc("log_kiosk_event", {
            "p_event": event,
            "p_hostname": platform.node(),
            "p_result": result,
            "p_message": message,
            "p_app_version": config.APP_VERSION,
            "p_candidate_id": candidate_id,
            "p_etablissement_id": etablissement_id,
        }).execute()
    except Exception as exc:
        local_db.audit("remote_audit_log_failed", detail=f"{event}: {exc}")
