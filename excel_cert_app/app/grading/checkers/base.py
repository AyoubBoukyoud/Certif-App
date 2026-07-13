"""Checker registry and result type.

A checker is a callable ``fn(ctx, params) -> CheckResult`` registered under a
``type`` string that matches the ``type=`` attribute of a ``<check>`` element.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..context import GradingContext


@dataclass
class CheckResult:
    passed: bool
    reason: str


CheckerFn = Callable[[GradingContext, dict], CheckResult]
REGISTRY: dict[str, CheckerFn] = {}


def checker(name: str):
    def deco(fn: CheckerFn) -> CheckerFn:
        REGISTRY[name] = fn
        return fn
    return deco


def ok(reason: str = "OK") -> CheckResult:
    return CheckResult(True, reason)


def fail(reason: str) -> CheckResult:
    return CheckResult(False, reason)


# -- small parsing helpers reused across checkers --------------------------


def as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "oui", "on")


def as_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
