-- Certif-App — makes deleting a complexe or établissement a real cascade,
-- instead of the "blocked while dependents exist" behavior handleDelete had
-- until now (see supabase/functions/manage-user/index.ts's rewritten
-- handleDelete, deployed alongside this migration).
--
-- After this migration:
--   DELETE FROM complexes WHERE id = X
--     -> cascades to its établissements, which cascades further to their
--        candidats, surveillant/établissement profiles, exam_schedules,
--        excel_imports, and those exam_schedules' exam_sessions — plus the
--        complexe's own profile (profiles.complexe_id).
--   DELETE FROM etablissements WHERE id = X
--     -> same cascade, one level down (its own subtree only).
-- This is genuinely irreversible — there is no soft-delete/trash here.
--
-- Historical/audit rows are deliberately NOT deleted, only unlinked
-- (ON DELETE SET NULL): incident_reports, audit_logs, and every `created_by`/
-- `validated_by`/`reported_by`/`actor` creator reference — losing an
-- établissement shouldn't erase the audit trail that mentions it.
--
-- regions and auth.users are untouched by this file on purpose: deleting a
-- complexe/établissement never deletes the region above it, and profiles-to-
-- auth.users cleanup for a cascaded-away profile is handled in the Edge
-- Function (it has no cascade here — see that function's comment).
--
-- Run once, in full, via the Supabase project's SQL Editor, AFTER 0001-0005.
-- Safe to re-run (every statement is DROP-then-ADD), but pointless to.

-- ============================================================================
-- Real cascade: rows that belong to the deleted complexe/établissement.
-- ============================================================================

alter table etablissements drop constraint etablissements_complexe_id_fkey;
alter table etablissements add constraint etablissements_complexe_id_fkey
  foreign key (complexe_id) references complexes(id) on delete cascade;

alter table profiles drop constraint profiles_complexe_id_fkey;
alter table profiles add constraint profiles_complexe_id_fkey
  foreign key (complexe_id) references complexes(id) on delete cascade;

alter table profiles drop constraint profiles_etablissement_id_fkey;
alter table profiles add constraint profiles_etablissement_id_fkey
  foreign key (etablissement_id) references etablissements(id) on delete cascade;

alter table exam_schedules drop constraint exam_schedules_etablissement_id_fkey;
alter table exam_schedules add constraint exam_schedules_etablissement_id_fkey
  foreign key (etablissement_id) references etablissements(id) on delete cascade;

alter table excel_imports drop constraint excel_imports_etablissement_id_fkey;
alter table excel_imports add constraint excel_imports_etablissement_id_fkey
  foreign key (etablissement_id) references etablissements(id) on delete cascade;

alter table candidates drop constraint candidates_etablissement_id_fkey;
alter table candidates add constraint candidates_etablissement_id_fkey
  foreign key (etablissement_id) references etablissements(id) on delete cascade;

alter table exam_sessions drop constraint exam_sessions_candidate_id_fkey;
alter table exam_sessions add constraint exam_sessions_candidate_id_fkey
  foreign key (candidate_id) references candidates(id) on delete cascade;

alter table exam_sessions drop constraint exam_sessions_exam_schedule_id_fkey;
alter table exam_sessions add constraint exam_sessions_exam_schedule_id_fkey
  foreign key (exam_schedule_id) references exam_schedules(id) on delete cascade;

-- ============================================================================
-- Unlink, don't delete: historical/reference columns.
-- ============================================================================

alter table candidates drop constraint candidates_exam_schedule_id_fkey;
alter table candidates add constraint candidates_exam_schedule_id_fkey
  foreign key (exam_schedule_id) references exam_schedules(id) on delete set null;

alter table candidates drop constraint candidates_import_batch_id_fkey;
alter table candidates add constraint candidates_import_batch_id_fkey
  foreign key (import_batch_id) references excel_imports(id) on delete set null;

alter table excel_imports drop constraint excel_imports_exam_schedule_id_fkey;
alter table excel_imports add constraint excel_imports_exam_schedule_id_fkey
  foreign key (exam_schedule_id) references exam_schedules(id) on delete set null;

alter table incident_reports drop constraint incident_reports_exam_schedule_id_fkey;
alter table incident_reports add constraint incident_reports_exam_schedule_id_fkey
  foreign key (exam_schedule_id) references exam_schedules(id) on delete set null;

alter table complexes drop constraint complexes_created_by_fkey;
alter table complexes add constraint complexes_created_by_fkey
  foreign key (created_by) references profiles(id) on delete set null;

alter table etablissements drop constraint etablissements_created_by_fkey;
alter table etablissements add constraint etablissements_created_by_fkey
  foreign key (created_by) references profiles(id) on delete set null;

alter table exam_schedules drop constraint exam_schedules_created_by_fkey;
alter table exam_schedules add constraint exam_schedules_created_by_fkey
  foreign key (created_by) references profiles(id) on delete set null;

alter table excel_imports drop constraint excel_imports_created_by_fkey;
alter table excel_imports add constraint excel_imports_created_by_fkey
  foreign key (created_by) references profiles(id) on delete set null;

alter table exam_sessions drop constraint exam_sessions_validated_by_fkey;
alter table exam_sessions add constraint exam_sessions_validated_by_fkey
  foreign key (validated_by) references profiles(id) on delete set null;

alter table incident_reports drop constraint incident_reports_reported_by_fkey;
alter table incident_reports add constraint incident_reports_reported_by_fkey
  foreign key (reported_by) references profiles(id) on delete set null;

alter table audit_logs drop constraint audit_logs_actor_fkey;
alter table audit_logs add constraint audit_logs_actor_fkey
  foreign key (actor) references profiles(id) on delete set null;

alter table audit_logs drop constraint audit_logs_candidate_id_fkey;
alter table audit_logs add constraint audit_logs_candidate_id_fkey
  foreign key (candidate_id) references candidates(id) on delete set null;

alter table audit_logs drop constraint audit_logs_etablissement_id_fkey;
alter table audit_logs add constraint audit_logs_etablissement_id_fkey
  foreign key (etablissement_id) references etablissements(id) on delete set null;
