"""End-to-end smoke test of the controller flow (offscreen, stub Excel)."""
import os
import tempfile

os.environ.setdefault("EXCEL_CERT_DATA_DIR", tempfile.mkdtemp(prefix="excel_cert_flow_"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from app.db.dao import Database  # noqa: E402
from app.exam.session import ExamSession, ExamState  # noqa: E402


def test_full_session_flow_offscreen():
    app = QApplication.instance() or QApplication([])
    db = Database(tempfile.mktemp(suffix=".sqlite3"))
    db.set_admin_code("1234")

    session = ExamSession(db)
    cid = db.create_candidate("Test", "User", "AB123456", "0612345678")
    session.create(cid, "A")
    assert len(session.project_nos) == 7

    session.start()
    assert session.state == ExamState.RUNNING
    assert 0 < session.remaining_seconds() <= 50 * 60

    # Mark a task and submit every project.
    for _ in range(7):
        proj = session.current_project()
        session.mark_task(proj.tasks[0].id, complete=True)
        assert session.current_marks()[proj.tasks[0].id]["complete"]
        session.submit_current()
        session.advance_after_submit()

    assert session.all_submitted()
    result = session.grade()
    assert result.total_tasks == sum(len(p.tasks) for p in session.projects.values())
    assert 0.0 <= result.score_pct <= 100.0
    assert db.get_session(session.session_id).status == "finished"
    assert not result.passed  # nothing actually done in Excel -> should fail


def test_resume_after_interrupt():
    app = QApplication.instance() or QApplication([])
    db = Database(tempfile.mktemp(suffix=".sqlite3"))
    s1 = ExamSession(db)
    cid = db.create_candidate("R", "S", "X1", "0600000000")
    s1.create(cid, "B")
    s1.start()
    s1.submit_current()
    s1.advance_after_submit()
    sid = s1.session_id

    # New session object resumes the interrupted one.
    s2 = ExamSession(db)
    s2.resume(sid)
    assert s2.session_id == sid
    assert s2.state == ExamState.RUNNING
    # First project was submitted, so resume points at project 2.
    assert s2.current_index == 1
