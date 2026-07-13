"""Exam session state machine and orchestration.

UI-agnostic: the controller drives it and reads state back. It owns the
persistence calls (via the DAO), the working files (via workdir) and the timer.
Grading is delegated to the grading engine, imported lazily to avoid a hard
dependency for parts of the app that never grade.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass

from .. import config, content
from ..db.dao import Candidate, Database, SessionProject
from . import timer, variants, workdir


class ExamState(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    REVIEWING = "reviewing"
    GRADING = "grading"
    RESULTS = "results"
    ABORTED = "aborted"


@dataclass
class GradeResult:
    score_pct: float
    passed: bool
    passed_tasks: int
    total_tasks: int
    per_project: dict[int, tuple[int, int]]  # project_no -> (passed, total)


class ExamSession:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.state = ExamState.IDLE
        self.session_id: int | None = None
        self.candidate: Candidate | None = None
        self.variant: str = "A"
        self.project_nos: list[int] = []
        self.projects: dict[int, content.Project] = {}
        self.current_index: int = 0
        self.exam_minutes: int = config.DEFAULT_EXAM_MINUTES
        self.pass_threshold: int = config.DEFAULT_PASS_THRESHOLD

    # -- lifecycle ---------------------------------------------------------

    def create(self, candidate_id: int, variant: str) -> None:
        self.candidate = self.db.get_candidate(candidate_id)
        self.variant = variant
        self.exam_minutes = self.db.get_int_setting(
            "exam_minutes", config.DEFAULT_EXAM_MINUTES
        )
        self.pass_threshold = self.db.get_int_setting(
            "pass_threshold", config.DEFAULT_PASS_THRESHOLD
        )
        self.project_nos = variants.project_list(variant)
        self.session_id = self.db.create_session(candidate_id, variant)

        for idx, pno in enumerate(self.project_nos):
            wf = workdir.prepare_project(self.session_id, pno)
            self.db.create_session_project(self.session_id, pno, idx, str(wf))
            self.projects[pno] = content.load_project_cached(pno)

    def start(self) -> None:
        assert self.session_id is not None
        started = timer.now()
        deadline = timer.compute_deadline(started, self.exam_minutes)
        self.db.start_session(
            self.session_id, started.isoformat(timespec="seconds"),
            deadline.isoformat(timespec="seconds"),
        )
        self.current_index = 0
        self.state = ExamState.RUNNING
        self.db.audit("exam_started", self.session_id, f"variant={self.variant}")

    def resume(self, session_id: int) -> None:
        """Rehydrate a session that was interrupted (crash / restart)."""
        s = self.db.get_session(session_id)
        assert s is not None
        self.session_id = session_id
        self.candidate = self.db.get_candidate(s.candidate_id)
        self.variant = s.variant
        self.exam_minutes = self.db.get_int_setting(
            "exam_minutes", config.DEFAULT_EXAM_MINUTES
        )
        self.pass_threshold = self.db.get_int_setting(
            "pass_threshold", config.DEFAULT_PASS_THRESHOLD
        )
        sps = self.db.list_session_projects(session_id)
        self.project_nos = [sp.project_no for sp in sps]
        for pno in self.project_nos:
            self.projects[pno] = content.load_project_cached(pno)
        # Resume at the first not-yet-submitted project.
        pending = [i for i, sp in enumerate(sps) if sp.submitted_at is None]
        self.current_index = pending[0] if pending else 0
        self.state = ExamState.RUNNING if pending else ExamState.REVIEWING
        self.db.audit("resume_after_crash", session_id)

    # -- navigation --------------------------------------------------------

    @property
    def session_projects(self) -> list[SessionProject]:
        assert self.session_id is not None
        return self.db.list_session_projects(self.session_id)

    def current_project_no(self) -> int:
        return self.project_nos[self.current_index]

    def current_project(self) -> content.Project:
        return self.projects[self.current_project_no()]

    def current_session_project(self) -> SessionProject:
        pno = self.current_project_no()
        return next(sp for sp in self.session_projects if sp.project_no == pno)

    def display_position(self) -> tuple[int, int]:
        """1-based (index, total) for the 'Projet i sur n' label."""
        return self.current_index + 1, len(self.project_nos)

    # -- marks -------------------------------------------------------------

    def mark_task(
        self, task_no: int, *, complete: bool | None = None, review: bool | None = None
    ) -> None:
        sp = self.current_session_project()
        self.db.upsert_task_mark(
            sp.id, task_no, marked_complete=complete, marked_review=review
        )

    def current_marks(self) -> dict[int, dict]:
        return self.db.get_task_marks(self.current_session_project().id)

    # -- submit / reopen ---------------------------------------------------

    def submit_current(self) -> None:
        sp = self.current_session_project()
        self.db.mark_project_submitted(sp.id)
        self.db.audit("project_submitted", self.session_id, f"project={sp.project_no}")

    def advance_after_submit(self) -> bool:
        """Move to the next unsubmitted project. Returns False if none remain."""
        sps = {sp.project_no: sp for sp in self.session_projects}
        for i, pno in enumerate(self.project_nos):
            if sps[pno].submitted_at is None:
                self.current_index = i
                return True
        self.state = ExamState.REVIEWING
        return False

    def all_submitted(self) -> bool:
        return all(sp.submitted_at is not None for sp in self.session_projects)

    def reopen(self, project_no: int) -> None:
        sp = next(s for s in self.session_projects if s.project_no == project_no)
        self.db.increment_reopened(sp.id)
        self.current_index = self.project_nos.index(project_no)
        self.state = ExamState.RUNNING
        self.db.audit("project_reopened", self.session_id, f"project={project_no}")

    # -- timing ------------------------------------------------------------

    def remaining_seconds(self) -> int:
        assert self.session_id is not None
        s = self.db.get_session(self.session_id)
        if not s or not s.deadline:
            return self.exam_minutes * 60
        return timer.remaining_seconds(timer.parse(s.deadline))

    def elapsed_seconds(self) -> int:
        assert self.session_id is not None
        s = self.db.get_session(self.session_id)
        if not s or not s.started_at:
            return 0
        return int((timer.now() - timer.parse(s.started_at)).total_seconds())

    # -- grading / finish --------------------------------------------------

    def grade(self) -> GradeResult:
        from ..grading.engine import GradingEngine

        self.state = ExamState.GRADING
        engine = GradingEngine()
        per_project: dict[int, tuple[int, int]] = {}

        for sp in self.session_projects:
            project = self.projects[sp.project_no]
            outcomes = engine.grade_project(project, sp.workfile_path)
            p_pass = 0
            for task_no, (ok, details) in outcomes.items():
                self.db.set_task_grade(sp.id, task_no, ok, details)
                p_pass += 1 if ok else 0
            per_project[sp.project_no] = (p_pass, len(project.tasks))

        passed_tasks, total_tasks = self.db.count_session_tasks(self.session_id)
        score = (passed_tasks / total_tasks * 100.0) if total_tasks else 0.0
        passed = score >= self.pass_threshold

        self.db.finish_session(
            self.session_id, self.elapsed_seconds(), score, passed
        )
        result = GradeResult(
            score, passed, passed_tasks, total_tasks, per_project
        )
        self.state = ExamState.RESULTS
        self.db.audit(
            "exam_graded", self.session_id,
            f"score={score:.1f} passed={passed}",
        )
        return result

    def abort(self) -> None:
        if self.session_id is not None:
            self.db.abort_session(self.session_id)
            self.db.audit("exam_aborted", self.session_id)
        self.state = ExamState.ABORTED

    def cleanup(self) -> None:
        if self.session_id is not None:
            workdir.archive_session(self.session_id)
