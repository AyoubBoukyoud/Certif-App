"""Database / DAO tests."""
import os
import tempfile

os.environ.setdefault("EXCEL_CERT_DATA_DIR", tempfile.mkdtemp(prefix="excel_cert_test_"))

from app.db.dao import Database  # noqa: E402


def _fresh_db():
    path = tempfile.mktemp(suffix=".sqlite3")
    return Database(path)


def test_admin_code():
    db = _fresh_db()
    assert not db.is_admin_code_set()
    db.set_admin_code("1234")
    assert db.is_admin_code_set()
    assert db.verify_admin_code("1234")
    assert not db.verify_admin_code("9999")


def test_session_lifecycle_and_scoring():
    db = _fresh_db()
    cid = db.create_candidate("Amina", "Zahiri", "AB123456", "0612345678")
    sid = db.create_session(cid, "A")
    assert db.get_running_session().id == sid

    sp = db.create_session_project(sid, 1, 0, "/tmp/P1.xlsx")
    db.upsert_task_mark(sp, 1, marked_complete=True)
    marks = db.get_task_marks(sp)
    assert marks[1]["complete"] is True

    db.set_task_grade(sp, 1, True, {"r": "ok"})
    db.set_task_grade(sp, 2, False, {"r": "no"})
    passed, total = db.count_session_tasks(sid)
    assert (passed, total) == (1, 2)

    db.finish_session(sid, 1200, 50.0, False)
    assert db.get_session(sid).status == "finished"
    assert db.get_running_session() is None


def test_task_mark_toggle_preserves_other_flag():
    db = _fresh_db()
    cid = db.create_candidate("A", "B", "X1", "0600000000")
    sid = db.create_session(cid, "A")
    sp = db.create_session_project(sid, 1, 0, "/tmp/P1.xlsx")
    db.upsert_task_mark(sp, 1, marked_complete=True)
    db.upsert_task_mark(sp, 1, marked_review=True)   # must not wipe 'complete'
    marks = db.get_task_marks(sp)
    assert marks[1] == {"complete": True, "review": True}
