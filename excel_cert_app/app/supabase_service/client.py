"""Supabase client wrapper for the desktop kiosk.

Reads connection settings from the environment (loaded from `.env` if
present). The kiosk only ever holds the *publishable* key here — an
établissement/surveillant identity comes from `sign_in_with_password`, and
Postgres RLS (see ../../../supabase/migrations/) then scopes what that
session can see. The secret/service-role key is for server-side admin
scripts only and must never be loaded by this module.

Two client-construction functions, for two different lifetimes:
- ``get_client()`` — a process-wide singleton, never authenticated. Used for
  the public `lookup_candidate_by_cin` / `log_kiosk_event` RPCs (see
  candidates.py / audit.py), which need no session at all.
- ``new_client()`` — a fresh, uncached instance. Used for the one-off
  supervisor sign-in (Écran 3): its session must not leak into the shared
  singleton held by ``get_client()``.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_PUBLISHABLE_KEY: str = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")


class SupabaseNotConfigured(RuntimeError):
    """Raised when SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY are missing."""


def new_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise SupabaseNotConfigured(
            "SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY missing — check .env "
            "(see .env.example)."
        )
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


@lru_cache(maxsize=1)
def get_client() -> Client:
    return new_client()
