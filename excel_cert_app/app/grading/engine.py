"""Grading engine.

Runs a project's tasks against a candidate workbook and returns, per task,
whether it passed plus a details payload (each requirement's outcome) suitable
for storing as JSON and for admin review.
"""
from __future__ import annotations

import traceback
from pathlib import Path

from .. import config
from ..content import AnyGroup, Check, Project, Task
from . import checkers  # noqa: F401  (populates the registry)
from .checkers.base import REGISTRY, CheckResult
from .context import GradingContext


def _solution_path(project_no: int) -> Path | None:
    p = config.SOLUTIONS_DIR / f"projet{project_no}.xlsx"
    return p if p.exists() else None


class GradingEngine:
    def run_check(self, ctx: GradingContext, chk: Check) -> CheckResult:
        fn = REGISTRY.get(chk.type)
        if fn is None:
            return CheckResult(False, f"vérificateur inconnu: {chk.type}")
        try:
            return fn(ctx, chk.params)
        except Exception as exc:  # a broken checker must never abort grading
            return CheckResult(
                False, f"erreur du vérificateur {chk.type}: {exc}\n"
                       f"{traceback.format_exc(limit=2)}"
            )

    def _evaluate_requirement(self, ctx: GradingContext, req) -> tuple[bool, dict]:
        if isinstance(req, AnyGroup):
            results = [self.run_check(ctx, c) for c in req.checks]
            passed = any(r.passed for r in results)
            return passed, {
                "any": [{"type": c.type, "passed": r.passed, "reason": r.reason}
                        for c, r in zip(req.checks, results)]
            }
        result = self.run_check(ctx, req)
        return result.passed, {"type": req.type, "passed": result.passed,
                               "reason": result.reason}

    def grade_task(self, ctx: GradingContext, task: Task) -> tuple[bool, dict]:
        details: list[dict] = []
        all_ok = True
        for req in task.requirements:
            passed, info = self._evaluate_requirement(ctx, req)
            details.append(info)
            all_ok = all_ok and passed
        if not task.requirements:
            all_ok = False
            details.append({"reason": "aucune vérification définie"})
        return all_ok, {"task": task.id, "passed": all_ok, "checks": details}

    def grade_project(
        self, project: Project, user_path: str | Path
    ) -> dict[int, tuple[bool, dict]]:
        pristine = config.project_workbook(project.id)
        ctx = GradingContext(user_path, pristine, _solution_path(project.id))
        try:
            return {t.id: self.grade_task(ctx, t) for t in project.tasks}
        finally:
            ctx.close()
