"""Network/clock probes for the System Check screen (Écran 1).

Kept separate from ``client.py`` because these run *before* anything needs a
signed-in Supabase session — a plain HTTP HEAD is enough to know whether the
platform is reachable at all, and its response ``Date`` header doubles as a
free clock-skew reference without a separate NTP round-trip.
"""
from __future__ import annotations

import socket
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from .client import SUPABASE_URL

_TIMEOUT_S = 5


def check_internet() -> bool:
    """Best-effort: a short TCP connect to a well-known, stable host."""
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=_TIMEOUT_S):
            return True
    except OSError:
        return False


def check_supabase() -> tuple[bool, datetime | None]:
    """Returns (reachable, server_time). ``server_time`` is parsed from the
    response's ``Date`` header when available, for the clock-skew check —
    never raises, a failure just means (False, None)."""
    if not SUPABASE_URL:
        return False, None
    try:
        resp = httpx.head(f"{SUPABASE_URL}/auth/v1/health", timeout=_TIMEOUT_S)
        server_time = None
        date_header = resp.headers.get("Date")
        if date_header:
            try:
                server_time = parsedate_to_datetime(date_header)
            except (TypeError, ValueError):
                server_time = None
        return resp.status_code < 500, server_time
    except httpx.HTTPError:
        return False, None


def clock_skew_seconds(server_time: datetime | None) -> float | None:
    if server_time is None:
        return None
    if server_time.tzinfo is None:
        server_time = server_time.replace(tzinfo=timezone.utc)
    return abs((datetime.now(timezone.utc) - server_time).total_seconds())
