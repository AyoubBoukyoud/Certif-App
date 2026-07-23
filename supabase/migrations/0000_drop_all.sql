-- Certif-App online platform — full reset, part 1/2: drop everything.
--
-- Run this FIRST, alone, in the Supabase SQL Editor. Then run
-- 0001_full_schema.sql to recreate everything under its final structure.
--
-- Only touches the `public` schema — does NOT touch `auth.users`. If you
-- want test accounts gone too, delete them separately under
-- Authentication -> Users in the dashboard.
--
-- Safe to re-run: every statement is `if exists`, so nothing errors if some
-- or all of this was already dropped.

drop table if exists incident_reports cascade;
drop table if exists exam_sessions cascade;
drop table if exists candidates cascade;
drop table if exists excel_imports cascade;
drop table if exists exam_schedules cascade;
drop table if exists audit_logs cascade;
drop table if exists profiles cascade;
drop table if exists etablissements cascade;
drop table if exists complexes cascade;
drop table if exists regions cascade;

-- Pre-rename / abandoned-draft names from earlier iterations, dropped
-- defensively so the recreate script never collides with a leftover table.
drop table if exists stagiaire_imports cascade;
drop table if exists exam_attempts cascade;
drop table if exists stagiaires cascade;
drop table if exists audit_log cascade;
drop table if exists attendance cascade;
drop table if exists notifications cascade;
drop table if exists files cascade;
drop table if exists role_permissions cascade;
drop table if exists permissions cascade;
drop table if exists roles cascade;
drop view if exists national_stats cascade;

drop function if exists my_role() cascade;
drop function if exists my_region_id() cascade;
drop function if exists my_complexe_id() cascade;
drop function if exists my_etablissement_id() cascade;
drop function if exists current_user_role() cascade;
drop function if exists current_entity_id() cascade;

drop type if exists user_role cascade;
