"""Admin/logout secret-code hashing.

Uses PBKDF2-HMAC-SHA256 from the standard library (no third-party crypto).
The code is never stored in clear text; only salt + derived hash live in the
settings table.
"""
from __future__ import annotations

import hashlib
import hmac
import os

_ITERATIONS = 200_000
_ALGO = "sha256"
_DK_LEN = 32


def hash_code(code: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for a plaintext code."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(_ALGO, code.encode("utf-8"), salt, _ITERATIONS, _DK_LEN)
    return salt.hex(), dk.hex()


def verify_code(code: str, salt_hex: str, hash_hex: str) -> bool:
    """Constant-time verification of a plaintext code against stored values."""
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    _, candidate = hash_code(code, salt)
    return hmac.compare_digest(candidate, hash_hex)
