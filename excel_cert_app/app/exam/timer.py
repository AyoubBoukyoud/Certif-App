"""Wall-clock exam timer.

The remaining time is always derived from a persisted ``deadline`` timestamp,
never from a decrementing counter. That way an app crash / restart resumes with
the correct time left instead of gifting the candidate extra minutes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def compute_deadline(started_at: datetime, minutes: int) -> datetime:
    return started_at + timedelta(minutes=minutes)


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def remaining_seconds(deadline: datetime, ref: datetime | None = None) -> int:
    ref = ref or now()
    return max(0, int((deadline - ref).total_seconds()))


def format_mmss(seconds: int) -> str:
    seconds = max(0, seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
