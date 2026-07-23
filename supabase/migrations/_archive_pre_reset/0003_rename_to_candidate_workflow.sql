-- Certif-App online platform — P4 (desktop candidate workflow).
-- Renames the P1 schema (0001_init_schema.sql) to the vocabulary of the
-- desktop cahier des charges, and adds the columns that vocabulary needs.
--
-- Note: a "0002_extend_schema.sql" exists in this same migrations folder,
-- written by a parallel effort on the *old* (stagiaires/exam_attempts)
-- naming, adding attendance/incident_reports/notifications/files/roles
-- catalogue tables. As of this writing neither 0002 nor this file (0003) has
-- been applied to the live project (verified live via the REST API —
-- `stagiaires.sexe` / old `exam_sessions.room` / `attendance` /
-- `national_stats` all 404). **Do not apply both** — 0002 alters
-- `exam_sessions`/`stagiaires` by their pre-rename names and would break
-- once 0003 has renamed them (and vice versa if 0002 runs first, its status
-- values ('planned'/'in_progress'/...) would conflict with 0003's own
-- ('started'/'terminated') on the table 0003 renames into `exam_sessions`).
-- This migration folds in the candidate/schedule columns the desktop
-- workflow actually needs directly, so it does not depend on 0002 having
-- run. The rest of 0002's draft (attendance, incident_reports,
-- notifications, files, roles/permissions catalogue) is out of scope here —
-- see ~/.claude/plans/harmonic-cuddling-flask.md §11.
--
-- Run once, in full, via the Supabase project's SQL Editor
-- (https://supabase.com/dashboard/project/pummdlglelbsviokubxw/sql/new).
--
-- Renaming a table does not break policies, foreign keys, or indexes that
-- reference it — Postgres tracks them by OID, not by name — so the RLS
-- policies created in 0001 keep working unchanged after the renames below.

-- ---------------------------------------------------------------------------
-- 1. Renames
-- ---------------------------------------------------------------------------

-- Free up the "exam_sessions" name for its new per-candidate meaning below —
-- must run before renaming exam_attempts, to avoid a name collision.
alter table exam_sessions rename to exam_schedules;

alter table stagiaires rename to candidates;
alter table candidates rename column exam_session_id to exam_schedule_id;

alter table exam_attempts rename to exam_sessions;
alter table exam_sessions rename column stagiaire_id to candidate_id;
alter table exam_sessions rename column exam_session_id to exam_schedule_id;

alter table audit_log rename to audit_logs;

-- `stagiaire_imports` (Excel import audit trail) is unrelated to the desktop
-- workflow covered by this migration — left as-is, out of scope here (its
-- `exam_session_id` FK still resolves correctly to `exam_schedules` by OID
-- even though the column name did not follow the rename).

-- ---------------------------------------------------------------------------
-- 2. New columns
-- ---------------------------------------------------------------------------

-- candidates — Écran 2 fields not already covered by existing columns or by
-- the etablissement -> region / exam_schedule joins.
alter table candidates add column if not exists sexe text;
alter table candidates add column if not exists filiere text;
alter table candidates add column if not exists groupe text;
alter table candidates add column if not exists photo_path text;

-- exam_schedules — logistics fields (Version MOS shown on the Écran 2 card,
-- room/duration informational).
alter table exam_schedules add column if not exists room text;
alter table exam_schedules add column if not exists duration_minutes int;
alter table exam_schedules add column if not exists mos_version text;

-- exam_sessions (ex exam_attempts) — Écran 3/5 fields: workstation identity
-- at validation time, and the started/terminated lifecycle.
alter table exam_sessions add column if not exists workstation text;
alter table exam_sessions add column if not exists hostname text;
alter table exam_sessions add column if not exists ip_local text;
alter table exam_sessions add column if not exists incidents jsonb;
alter table exam_sessions add column if not exists technical_logs jsonb;
alter table exam_sessions add column if not exists status text
  not null default 'started';
alter table exam_sessions add constraint exam_sessions_status_check
  check (status in ('started', 'terminated'));

-- audit_logs — Écran-agnostic logging fields from the cahier des charges
-- (utilisateur/candidat/surveillant already covered by `actor`;
-- ordinateur/résultat/message/version added here).
alter table audit_logs add column if not exists candidate_id uuid
  references candidates(id);
alter table audit_logs add column if not exists hostname text;
alter table audit_logs add column if not exists result text;
alter table audit_logs add column if not exists message text;
alter table audit_logs add column if not exists app_version text;

-- ---------------------------------------------------------------------------
-- 3. New RLS policy
-- ---------------------------------------------------------------------------

-- 0001 only granted SELECT on audit_log — the desktop kiosk now needs to
-- insert rows itself (system check, candidate lookup, supervisor
-- validation, exam finish). All remote audit writes funnel through the
-- kiosk's own établissement session (see app/supabase_service/audit.py),
-- never the ephemeral surveillant session, so a single policy covers it.
create policy audit_logs_insert_etablissement on audit_logs
  for insert with check (
    my_role() = 'etablissement'
    and (etablissement_id is null or etablissement_id = my_etablissement_id())
  );
