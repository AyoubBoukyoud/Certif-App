-- Schema for the Excel certification app. Applied idempotently at startup.
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS candidates (
    id          INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    cin         TEXT NOT NULL,
    birth_date  TEXT,
    institution TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY,
    candidate_id  INTEGER NOT NULL REFERENCES candidates(id),
    variant       TEXT NOT NULL CHECK (variant IN ('A', 'B')),
    started_at    TEXT,
    deadline      TEXT,
    ended_at      TEXT,
    duration_s    INTEGER,
    score_pct     REAL,
    passed        INTEGER,          -- 0/1
    status        TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'finished', 'aborted'))
);

CREATE TABLE IF NOT EXISTS session_projects (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    project_no      INTEGER NOT NULL,
    order_idx       INTEGER NOT NULL,
    workfile_path   TEXT,
    submitted_at    TEXT,
    reopened_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS task_results (
    id                  INTEGER PRIMARY KEY,
    session_project_id  INTEGER NOT NULL REFERENCES session_projects(id),
    task_no             INTEGER NOT NULL,
    marked_complete     INTEGER NOT NULL DEFAULT 0,
    marked_review       INTEGER NOT NULL DEFAULT 0,
    passed              INTEGER,      -- 0/1, NULL until graded
    checker_details     TEXT          -- JSON
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER,
    ts          TEXT NOT NULL,
    event       TEXT NOT NULL,
    detail      TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_status   ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sp_session         ON session_projects(session_id);
CREATE INDEX IF NOT EXISTS idx_tr_sp              ON task_results(session_project_id);
CREATE INDEX IF NOT EXISTS idx_audit_session      ON audit_log(session_id);
