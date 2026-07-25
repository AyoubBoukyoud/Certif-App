"""Candidate lookup for Écran 2 (Identification du candidat).

Goes through the `lookup_candidate_by_cin` RPC (see
../../../supabase/migrations/0002_kiosk_public_rpc.sql) rather than querying
`candidates`/`exam_schedules` directly: the kiosk no longer pairs to an
établissement account, so it has no session RLS would otherwise require for
a direct table read. The RPC applies the same "cin matches, exam_schedule
open and dated today" filter server-side. Multiple attempts per candidate
are allowed (product decision) — this does not check for a prior
exam_sessions row.
"""
from __future__ import annotations

from dataclasses import dataclass

from supabase import Client


@dataclass
class CandidateRecord:
    id: str
    first_name: str
    last_name: str
    cin: str
    birth_date: str | None
    sexe: str | None
    filiere: str | None
    groupe: str | None
    photo_path: str | None
    etablissement_id: str
    etablissement_name: str
    complexe_name: str | None
    region_name: str | None
    exam_schedule_id: str
    mos_version: str | None
    exam_date: str | None
    start_time: str | None


def find_by_cin(client: Client, cin: str) -> CandidateRecord | None:
    resp = client.rpc("lookup_candidate_by_cin", {"p_cin": cin}).execute()
    rows = resp.data or []
    if not rows:
        return None
    row = rows[0]
    return CandidateRecord(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        cin=row["cin"],
        birth_date=row.get("birth_date"),
        sexe=row.get("sexe"),
        filiere=row.get("filiere"),
        groupe=row.get("groupe"),
        photo_path=row.get("photo_path"),
        etablissement_id=row["etablissement_id"],
        etablissement_name=row.get("etablissement_name") or "",
        complexe_name=row.get("complexe_name"),
        region_name=row.get("region_name"),
        exam_schedule_id=row["exam_schedule_id"],
        mos_version=row.get("mos_version"),
        exam_date=row.get("exam_date"),
        start_time=row.get("start_time"),
    )
