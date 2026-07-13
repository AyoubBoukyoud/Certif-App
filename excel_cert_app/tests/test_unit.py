"""Unit tests for the locale-independent building blocks."""
import os
import tempfile

import pytest

os.environ.setdefault("EXCEL_CERT_DATA_DIR", tempfile.mkdtemp(prefix="excel_cert_test_"))

from app.exam import timer  # noqa: E402
from app.grading.formula_locale import normalize  # noqa: E402
from app.security import hash_code, verify_code  # noqa: E402


def test_formula_normalization():
    assert normalize("=MOYENNE(K2:K501)") == "AVERAGE(K2:K501)"
    assert normalize("=NB.SI(G8:G25;\">=12\")") == "COUNTIF(G8:G25,\">=12\")"
    assert normalize("=SOMME.SI(A1:A9;\">0\")") == "SUMIF(A1:A9,\">0\")"
    assert normalize("=MINUSCULE(A2)") == "LOWER(A2)"
    assert normalize(None) == ""


def test_security_roundtrip():
    salt, digest = hash_code("secret123")
    assert verify_code("secret123", salt, digest)
    assert not verify_code("wrong", salt, digest)


def test_timer_wall_clock():
    start = timer.now()
    deadline = timer.compute_deadline(start, 50)
    remaining = timer.remaining_seconds(deadline, ref=start)
    assert 50 * 60 - 1 <= remaining <= 50 * 60
    assert timer.format_mmss(125) == "02:05"
    assert timer.format_mmss(-10) == "00:00"


def test_variant_projects():
    from app import config

    assert config.VARIANT_PROJECTS["A"] == [1, 2, 3, 4, 5, 6, 7]
    assert config.VARIANT_PROJECTS["B"][0] == 1
    assert len(config.VARIANT_PROJECTS["B"]) == 7
