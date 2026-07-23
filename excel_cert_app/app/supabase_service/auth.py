"""Supabase Auth for the kiosk's one identity: a one-off **surveillant**
(supervisor) session at Écran 3, used only to validate the candidate and
create the `exam_sessions` row — never persisted (see `client.new_client`).

The kiosk itself no longer holds any établissement-level session: Écran 2's
candidate lookup goes through a public RPC (see `candidates.find_by_cin`)
that needs no prior authentication, and établissement scoping for the exam
is derived from whichever candidate is found rather than from a poste-level
pairing.
"""
from __future__ import annotations

from dataclasses import dataclass

from supabase import Client

from .client import new_client


class SupervisorAuthError(RuntimeError):
    pass


@dataclass
class SupervisorIdentity:
    profile_id: str
    full_name: str
    etablissement_id: str
    # The authenticated client from this sign-in — writes to `exam_sessions`
    # require an actual `surveillant` session per RLS (see 0001's
    # exam_attempts_insert/update_surveillant policies), so the caller keeps
    # this alive from Écran 3 through Écran 5 rather than re-authenticating.
    client: Client


def _fetch_profile(client, user_id: str) -> dict:
    resp = (
        client.table("profiles")
        .select("role, full_name, etablissement_id")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else {}


def sign_in_supervisor(
    login: str, password: str, *, expected_etablissement_id: str,
) -> SupervisorIdentity:
    """Écran 3. Uses a fresh, uncached client so this sign-in never replaces
    the kiosk's own établissement session (see `client.new_client`)."""
    client = new_client()
    try:
        result = client.auth.sign_in_with_password({"email": login, "password": password})
    except Exception as exc:
        raise SupervisorAuthError("Identifiants incorrects.") from exc
    if result.session is None or result.user is None:
        raise SupervisorAuthError("Identifiants incorrects.")
    profile = _fetch_profile(client, result.user.id)
    if profile.get("role") != "surveillant":
        raise SupervisorAuthError("Ce compte n'est pas un compte surveillant.")
    if profile.get("etablissement_id") != expected_etablissement_id:
        raise SupervisorAuthError(
            "Ce surveillant n'est pas affecté à cet établissement/cette session."
        )
    return SupervisorIdentity(
        profile_id=result.user.id,
        full_name=profile.get("full_name") or login,
        etablissement_id=profile["etablissement_id"],
        client=client,
    )
