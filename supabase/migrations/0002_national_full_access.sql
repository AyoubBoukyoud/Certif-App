-- Certif-App — grants the 'national' role full write access (insert/update/
-- delete) across every table that a regional/complexe/etablissement/
-- surveillant account can already write to, so a single national account can
-- act as a true super-admin: do everything Direction Régionale, Complexe de
-- Formation and Établissement can do, from one login.
--
-- 0001_full_schema.sql already gave 'national' unrestricted SELECT on every
-- table (see the `*_select_national` policies) — this file only adds the
-- missing INSERT/UPDATE/DELETE policies, unscoped (no region/complexe/
-- etablissement match required, unlike the role-specific policies below them
-- in 0001), since national sits above all of them in the hierarchy.
--
-- Run once, in full, via the Supabase project's SQL Editor, AFTER
-- 0001_full_schema.sql. Safe to run on top of a project that already has
-- 0001 applied; do NOT run twice (policy names are not idempotent — a second
-- run will fail on "policy already exists", which is intentional, same as
-- the rest of this migration chain).

-- ============================================================================
-- exam_schedules
-- ============================================================================

create policy exam_schedules_insert_national on exam_schedules
  for insert with check (my_role() = 'national');
create policy exam_schedules_update_national on exam_schedules
  for update using (my_role() = 'national');
create policy exam_schedules_delete_national on exam_schedules
  for delete using (my_role() = 'national');

-- ============================================================================
-- excel_imports
-- ============================================================================

create policy excel_imports_insert_national on excel_imports
  for insert with check (my_role() = 'national');
create policy excel_imports_update_national on excel_imports
  for update using (my_role() = 'national');

-- ============================================================================
-- candidates
-- ============================================================================

create policy candidates_insert_national on candidates
  for insert with check (my_role() = 'national');
create policy candidates_update_national on candidates
  for update using (my_role() = 'national');

-- ============================================================================
-- exam_sessions (per-candidate attempt)
-- ============================================================================

create policy exam_sessions_insert_national on exam_sessions
  for insert with check (my_role() = 'national');
create policy exam_sessions_update_national on exam_sessions
  for update using (my_role() = 'national');

-- ============================================================================
-- incident_reports
-- ============================================================================

create policy incident_reports_insert_national on incident_reports
  for insert with check (my_role() = 'national');

-- ============================================================================
-- audit_logs
-- ============================================================================

create policy audit_logs_insert_national on audit_logs
  for insert with check (my_role() = 'national');

-- Note: complexes / etablissements / profiles have no direct client-side
-- insert/update policies for ANY role (regional/complexe/etablissement
-- included) — those writes go exclusively through the `manage-user` Edge
-- Function using the service-role key, which bypasses RLS entirely. Granting
-- 'national' the ability to create regional/complexe/etablissement/
-- surveillant accounts is therefore done in that function (see
-- supabase/functions/manage-user/index.ts), not here.
