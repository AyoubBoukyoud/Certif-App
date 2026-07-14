"""SQLite data-access layer.

A single ``Database`` object owns one connection and exposes small,
purpose-built methods. Rows come back as ``sqlite3.Row`` (dict-like) or as
lightweight dataclasses where that reads better.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .. import config, security

_SCHEMA = Path(__file__).with_name("schema.sql")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Row dataclasses -------------------------------------------------------


@dataclass
class Candidate:
    id: int
    first_name: str
    last_name: str
    cin: str
    birth_date: str | None
    institution: str | None


@dataclass
class Session:
    id: int
    candidate_id: int
    variant: str
    started_at: str | None
    deadline: str | None
    ended_at: str | None
    duration_s: int | None
    score_pct: float | None
    passed: int | None
    status: str


@dataclass
class SessionProject:
    id: int
    session_id: int
    project_no: int
    order_idx: int
    workfile_path: str | None
    submitted_at: str | None
    reopened_count: int


class Database:
    def __init__(self, path: Path | str = config.DB_PATH) -> None:
        config.ensure_runtime_dirs()
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._apply_schema()

    def _apply_schema(self) -> None:
        self.conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
        self.conn.commit()
        self._migrate_candidates_table()

    def _migrate_candidates_table(self) -> None:
        """Upgrade a pre-existing ``candidates`` table (created before the
        birth_date/institution fields replaced phone) in place."""
        cols = {row["name"] for row in
                self.conn.execute("PRAGMA table_info(candidates)").fetchall()}
        if "birth_date" in cols and "institution" in cols and "phone" not in cols:
            return  # already on the current schema
        # sessions.candidate_id references candidates(id) with FK enforcement
        # on, so dropping candidates while any session rows exist would
        # violate that constraint — foreign_keys is a no-op mid-transaction,
        # so it must be toggled outside the executescript() below.
        self.conn.execute("PRAGMA foreign_keys = OFF")
        try:
            self.conn.executescript(
                """
                DROP TABLE IF EXISTS candidates_new;
                CREATE TABLE candidates_new (
                    id          INTEGER PRIMARY KEY,
                    first_name  TEXT NOT NULL,
                    last_name   TEXT NOT NULL,
                    cin         TEXT NOT NULL,
                    birth_date  TEXT,
                    institution TEXT,
                    created_at  TEXT NOT NULL
                );
                INSERT INTO candidates_new (id, first_name, last_name, cin, created_at)
                    SELECT id, first_name, last_name, cin, created_at FROM candidates;
                DROP TABLE candidates;
                ALTER TABLE candidates_new RENAME TO candidates;
                """
            )
            self.conn.commit()
        finally:
            self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.conn.close()

    # -- settings ----------------------------------------------------------

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def get_int_setting(self, key: str, default: int) -> int:
        v = self.get_setting(key)
        try:
            return int(v) if v is not None else default
        except ValueError:
            return default

    # -- admin code --------------------------------------------------------

    def is_admin_code_set(self) -> bool:
        return self.get_setting("admin_code_hash") is not None

    def set_admin_code(self, code: str) -> None:
        salt_hex, hash_hex = security.hash_code(code)
        self.set_setting("admin_code_salt", salt_hex)
        self.set_setting("admin_code_hash", hash_hex)

    def verify_admin_code(self, code: str) -> bool:
        salt = self.get_setting("admin_code_salt")
        digest = self.get_setting("admin_code_hash")
        if not salt or not digest:
            return False
        return security.verify_code(code, salt, digest)

    # -- candidates --------------------------------------------------------

    def create_candidate(
        self, first_name: str, last_name: str, cin: str,
        birth_date: str, institution: str,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO candidates(first_name, last_name, cin, birth_date, "
            "institution, created_at) VALUES(?, ?, ?, ?, ?, ?)",
            (first_name, last_name, cin, birth_date, institution, _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_candidate(self, candidate_id: int) -> Candidate | None:
        row = self.conn.execute(
            "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
        if not row:
            return None
        return Candidate(
            row["id"], row["first_name"], row["last_name"], row["cin"],
            row["birth_date"], row["institution"],
        )

    # -- sessions ----------------------------------------------------------

    def create_session(self, candidate_id: int, variant: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO sessions(candidate_id, variant, status) VALUES(?, ?, 'running')",
            (candidate_id, variant),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def start_session(self, session_id: int, started_at: str, deadline: str) -> None:
        self.conn.execute(
            "UPDATE sessions SET started_at = ?, deadline = ? WHERE id = ?",
            (started_at, deadline, session_id),
        )
        self.conn.commit()

    def get_session(self, session_id: int) -> Session | None:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return self._row_to_session(row) if row else None

    def get_running_session(self) -> Session | None:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE status = 'running' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return self._row_to_session(row) if row else None

    def finish_session(
        self, session_id: int, duration_s: int, score_pct: float, passed: bool
    ) -> None:
        self.conn.execute(
            "UPDATE sessions SET ended_at = ?, duration_s = ?, score_pct = ?, "
            "passed = ?, status = 'finished' WHERE id = ?",
            (_now(), duration_s, score_pct, 1 if passed else 0, session_id),
        )
        self.conn.commit()

    def abort_session(self, session_id: int) -> None:
        self.conn.execute(
            "UPDATE sessions SET ended_at = ?, status = 'aborted' WHERE id = ?",
            (_now(), session_id),
        )
        self.conn.commit()

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> Session:
        return Session(
            row["id"], row["candidate_id"], row["variant"], row["started_at"],
            row["deadline"], row["ended_at"], row["duration_s"],
            row["score_pct"], row["passed"], row["status"],
        )

    # -- session projects --------------------------------------------------

    def create_session_project(
        self, session_id: int, project_no: int, order_idx: int, workfile_path: str
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO session_projects"
            "(session_id, project_no, order_idx, workfile_path) VALUES(?, ?, ?, ?)",
            (session_id, project_no, order_idx, workfile_path),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_session_projects(self, session_id: int) -> list[SessionProject]:
        rows = self.conn.execute(
            "SELECT * FROM session_projects WHERE session_id = ? ORDER BY order_idx",
            (session_id,),
        ).fetchall()
        return [
            SessionProject(
                r["id"], r["session_id"], r["project_no"], r["order_idx"],
                r["workfile_path"], r["submitted_at"], r["reopened_count"],
            )
            for r in rows
        ]

    def mark_project_submitted(self, session_project_id: int) -> None:
        self.conn.execute(
            "UPDATE session_projects SET submitted_at = ? WHERE id = ?",
            (_now(), session_project_id),
        )
        self.conn.commit()

    def increment_reopened(self, session_project_id: int) -> None:
        self.conn.execute(
            "UPDATE session_projects SET reopened_count = reopened_count + 1 "
            "WHERE id = ?",
            (session_project_id,),
        )
        self.conn.commit()

    # -- task results ------------------------------------------------------

    def upsert_task_mark(
        self,
        session_project_id: int,
        task_no: int,
        *,
        marked_complete: bool | None = None,
        marked_review: bool | None = None,
    ) -> None:
        """Create the task row if needed and update the candidate's marks."""
        row = self.conn.execute(
            "SELECT id, marked_complete, marked_review FROM task_results "
            "WHERE session_project_id = ? AND task_no = ?",
            (session_project_id, task_no),
        ).fetchone()
        mc = marked_complete
        mr = marked_review
        if row is None:
            self.conn.execute(
                "INSERT INTO task_results"
                "(session_project_id, task_no, marked_complete, marked_review) "
                "VALUES(?, ?, ?, ?)",
                (session_project_id, task_no, int(bool(mc)), int(bool(mr))),
            )
        else:
            new_mc = int(bool(mc)) if mc is not None else row["marked_complete"]
            new_mr = int(bool(mr)) if mr is not None else row["marked_review"]
            self.conn.execute(
                "UPDATE task_results SET marked_complete = ?, marked_review = ? "
                "WHERE id = ?",
                (new_mc, new_mr, row["id"]),
            )
        self.conn.commit()

    def get_task_marks(self, session_project_id: int) -> dict[int, dict]:
        rows = self.conn.execute(
            "SELECT task_no, marked_complete, marked_review FROM task_results "
            "WHERE session_project_id = ?",
            (session_project_id,),
        ).fetchall()
        return {
            r["task_no"]: {
                "complete": bool(r["marked_complete"]),
                "review": bool(r["marked_review"]),
            }
            for r in rows
        }

    def set_task_grade(
        self, session_project_id: int, task_no: int, passed: bool, details: dict
    ) -> None:
        row = self.conn.execute(
            "SELECT id FROM task_results WHERE session_project_id = ? AND task_no = ?",
            (session_project_id, task_no),
        ).fetchone()
        payload = json.dumps(details, ensure_ascii=False)
        if row is None:
            self.conn.execute(
                "INSERT INTO task_results"
                "(session_project_id, task_no, passed, checker_details) "
                "VALUES(?, ?, ?, ?)",
                (session_project_id, task_no, int(passed), payload),
            )
        else:
            self.conn.execute(
                "UPDATE task_results SET passed = ?, checker_details = ? WHERE id = ?",
                (int(passed), payload, row["id"]),
            )
        self.conn.commit()

    def count_session_tasks(self, session_id: int) -> tuple[int, int]:
        """Return (passed, total) graded tasks for a session."""
        row = self.conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(passed), 0) AS passed "
            "FROM task_results tr JOIN session_projects sp "
            "ON tr.session_project_id = sp.id "
            "WHERE sp.session_id = ? AND tr.passed IS NOT NULL",
            (session_id,),
        ).fetchone()
        return int(row["passed"]), int(row["total"])

    # -- audit -------------------------------------------------------------

    def audit(self, event: str, session_id: int | None = None, detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO audit_log(session_id, ts, event, detail) VALUES(?, ?, ?, ?)",
            (session_id, _now(), event, detail),
        )
        self.conn.commit()
