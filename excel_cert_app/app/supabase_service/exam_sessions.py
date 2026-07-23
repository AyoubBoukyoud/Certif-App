"""Écran 3 → Écran 5: the per-candidate `exam_sessions` row (ex
`exam_attempts`, renamed in migration 0003) that bridges the desktop kiosk
to the platform — created at supervisor validation, closed out when the
exam finishes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client


def start(
    client: Client,
    *,
    candidate_id: str,
    exam_schedule_id: str,
    supervisor_id: str,
    workstation: str,
    hostname: str,
    ip_local: str | None,
) -> str:
    """Écran 3: creates the row with status='started'. Returns its id."""
    resp = (
        client.table("exam_sessions")
        .insert({
            "candidate_id": candidate_id,
            "exam_schedule_id": exam_schedule_id,
            "validated_by": supervisor_id,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "workstation": workstation,
            "hostname": hostname,
            "ip_local": ip_local,
            "status": "started",
        })
        .execute()
    )
    return resp.data[0]["id"]


def finish(
    client: Client,
    session_id: str,
    *,
    score_pct: float,
    passed: bool,
    desktop_session_uuid: str | None = None,
    incidents: dict | None = None,
    technical_logs: dict | None = None,
) -> None:
    """Écran 5: updates the row with the outcome and status='terminated'.
    Duration is not stored separately — it is `ended_at - started_at`,
    both already on the row."""
    payload = {
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "score_pct": score_pct,
        "passed": passed,
        "status": "terminated",
    }
    if desktop_session_uuid is not None:
        payload["desktop_session_uuid"] = desktop_session_uuid
    if incidents is not None:
        payload["incidents"] = incidents
    if technical_logs is not None:
        payload["technical_logs"] = technical_logs
    client.table("exam_sessions").update(payload).eq("id", session_id).execute()
