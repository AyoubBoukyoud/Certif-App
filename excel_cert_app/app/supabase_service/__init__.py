"""Connectivity to the Certif-App online platform (Supabase).

One small module per concern (client, auth, candidates, exam_sessions,
audit, connectivity) — see ~/.claude/plans/harmonic-cuddling-flask.md for the
desktop candidate workflow this supports. The kiosk holds no établissement
session; candidate lookup is a public RPC and établissement scoping comes
from whichever candidate is found (see candidates.py, auth.py).
"""
