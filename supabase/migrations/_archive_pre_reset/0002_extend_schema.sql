-- Certif-App online platform — extends 0001_init_schema.sql per the detailed
-- role/permission spec (plan §7, ~/.claude/plans/jiggly-hopping-cascade.md).
-- Additive only: no existing table is renamed or dropped. Vocabulary mapping
-- (spec -> existing schema) is documented in the plan, not repeated here.
--
-- Run this once, in full, via the Supabase project's SQL Editor
-- (https://supabase.com/dashboard/project/pummdlglelbsviokubxw/sql/new),
-- AFTER 0001_init_schema.sql has already been applied.

-- ---------------------------------------------------------------------------
-- 1. New tables
-- ---------------------------------------------------------------------------

create table attendance (
  id uuid primary key default gen_random_uuid(),
  exam_session_id uuid not null references exam_sessions(id),
  stagiaire_id uuid not null references stagiaires(id),
  present boolean not null,
  recorded_by uuid references profiles(id),
  recorded_at timestamptz not null default now(),
  unique (exam_session_id, stagiaire_id)
);

create table incident_reports (
  id uuid primary key default gen_random_uuid(),
  exam_session_id uuid not null references exam_sessions(id),
  reported_by uuid references profiles(id),
  description text not null,
  created_at timestamptz not null default now()
);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_id uuid not null references profiles(id),
  title text not null,
  body text,
  type text not null default 'info',
  read_at timestamptz,
  created_at timestamptz not null default now()
);

-- Generic file registry (exports, future avatars). The Storage bucket and
-- its own policies are created when the first real file feature is built,
-- not here.
create table files (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references profiles(id),
  category text not null,
  storage_path text not null,
  created_at timestamptz not null default now()
);

-- Read-only reference catalogue for the national dashboard's "platform
-- settings" screen — does NOT drive RLS (that stays on profiles.role, see
-- 0001's my_role()/my_region_id()/my_etablissement_id() helpers).
create table roles (
  id text primary key,
  label text not null,
  description text
);

create table permissions (
  id text primary key,
  label text not null
);

create table role_permissions (
  role_id text not null references roles(id),
  permission_id text not null references permissions(id),
  primary key (role_id, permission_id)
);

-- ---------------------------------------------------------------------------
-- 2. Extend existing tables
-- ---------------------------------------------------------------------------

alter table exam_sessions
  add column room text,
  add column duration_minutes int,
  add column mos_version text,
  add column workstation_count int;

update exam_sessions set status = 'planned' where status = 'scheduled';
alter table exam_sessions drop constraint exam_sessions_status_check;
alter table exam_sessions alter column status set default 'planned';
alter table exam_sessions add constraint exam_sessions_status_check
  check (status in ('planned', 'open', 'in_progress', 'finished', 'cancelled'));

-- Candidate columns from the Excel import spec. "Nom établissement" and
-- "Direction Régionale" are intentionally NOT duplicated as columns here —
-- already derivable via etablissement_id -> region_id; the import UI (P3
-- backlog) uses them only to validate consistency against the paired
-- établissement, not to store them redundantly.
alter table stagiaires
  add column sexe text,
  add column specialite text,
  add column groupe text,
  add column inscription_date date,
  add column filiere text,
  add column niveau text,
  add column email text;

-- ---------------------------------------------------------------------------
-- 3. Aggregate view for the national dashboard
-- ---------------------------------------------------------------------------

create view national_stats with (security_invoker = true) as
select
  (select count(*) from regions)        as regions_count,
  (select count(*) from etablissements) as etablissements_count,
  (select count(*) from profiles where role = 'surveillant') as surveillants_count,
  (select count(*) from stagiaires)     as candidats_count,
  (select count(*) from exam_sessions)  as examens_count;

-- ---------------------------------------------------------------------------
-- 4. Row Level Security
-- ---------------------------------------------------------------------------

alter table attendance enable row level security;
alter table incident_reports enable row level security;
alter table notifications enable row level security;
alter table files enable row level security;
alter table roles enable row level security;
alter table permissions enable row level security;
alter table role_permissions enable row level security;

-- attendance: same shape as exam_attempts policies in 0001.
create policy attendance_select_national on attendance
  for select using (my_role() = 'national');

create policy attendance_select_regional on attendance
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from exam_sessions s
      join etablissements e on e.id = s.etablissement_id
      where s.id = attendance.exam_session_id and e.region_id = my_region_id()
    )
  );

create policy attendance_select_etablissement on attendance
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and exists (
      select 1 from exam_sessions s
      where s.id = attendance.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

create policy attendance_write_surveillant on attendance
  for all using (
    my_role() = 'surveillant'
    and exists (
      select 1 from exam_sessions s
      where s.id = attendance.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  )
  with check (
    my_role() = 'surveillant'
    and exists (
      select 1 from exam_sessions s
      where s.id = attendance.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

-- incident_reports: same shape.
create policy incident_reports_select_national on incident_reports
  for select using (my_role() = 'national');

create policy incident_reports_select_regional on incident_reports
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from exam_sessions s
      join etablissements e on e.id = s.etablissement_id
      where s.id = incident_reports.exam_session_id and e.region_id = my_region_id()
    )
  );

create policy incident_reports_select_etablissement on incident_reports
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and exists (
      select 1 from exam_sessions s
      where s.id = incident_reports.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

create policy incident_reports_write_surveillant on incident_reports
  for all using (
    my_role() = 'surveillant'
    and exists (
      select 1 from exam_sessions s
      where s.id = incident_reports.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  )
  with check (
    my_role() = 'surveillant'
    and exists (
      select 1 from exam_sessions s
      where s.id = incident_reports.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

-- notifications: strictly self-scoped.
create policy notifications_select_self on notifications
  for select using (recipient_id = auth.uid());

create policy notifications_update_self on notifications
  for update using (recipient_id = auth.uid());

-- files: strictly owner-scoped.
create policy files_select_owner on files
  for select using (owner_id = auth.uid());

create policy files_insert_owner on files
  for insert with check (owner_id = auth.uid());

-- roles/permissions/role_permissions: read-only reference data for any
-- authenticated user (dashboard display only, never used by RLS itself).
create policy roles_select_authenticated on roles
  for select using (auth.role() = 'authenticated');

create policy permissions_select_authenticated on permissions
  for select using (auth.role() = 'authenticated');

create policy role_permissions_select_authenticated on role_permissions
  for select using (auth.role() = 'authenticated');

-- ---------------------------------------------------------------------------
-- 5. Seed the roles/permissions catalogue (per the spec's bullet lists)
-- ---------------------------------------------------------------------------

insert into roles (id, label, description) values
  ('national', 'Direction Nationale', 'Super admin — tous les droits sur toutes les régions.'),
  ('regional', 'Direction Régionale', 'Gère uniquement les établissements et sessions de sa région.'),
  ('etablissement', 'Administration d''établissement', 'Gère uniquement ses propres candidats et surveillants.'),
  ('surveillant', 'Surveillant', 'Voit uniquement les examens qui lui sont affectés.');

insert into permissions (id, label) values
  ('create_regional_direction', 'Créer une Direction Régionale'),
  ('edit_regional_direction', 'Modifier une Direction Régionale'),
  ('delete_regional_direction', 'Supprimer une Direction Régionale'),
  ('view_all_exams', 'Consulter tous les examens'),
  ('view_all_stats', 'Consulter toutes les statistiques'),
  ('view_all_etablissements', 'Consulter tous les établissements'),
  ('view_all_surveillants', 'Consulter tous les surveillants'),
  ('view_all_candidates', 'Consulter tous les candidats'),
  ('export_reports', 'Exporter des rapports'),
  ('manage_platform_settings', 'Gérer les paramètres de la plateforme'),
  ('create_etablissement', 'Créer un établissement'),
  ('edit_etablissement', 'Modifier un établissement'),
  ('disable_etablissement', 'Désactiver un établissement'),
  ('create_surveillant_account', 'Créer les comptes des surveillants'),
  ('create_exam_session', 'Créer les sessions d''examen'),
  ('assign_exam_session', 'Affecter établissement/surveillant/date/heure/candidats'),
  ('view_region_exams', 'Consulter les examens de sa région'),
  ('view_region_candidates', 'Consulter les candidats de sa région'),
  ('view_region_results', 'Consulter les résultats de sa région'),
  ('view_region_history', 'Consulter l''historique de sa région'),
  ('export_region_reports', 'Exporter rapports Excel/PDF de sa région'),
  ('import_candidates_excel', 'Importer un fichier Excel de candidats'),
  ('view_own_candidates', 'Consulter la liste de ses candidats'),
  ('view_own_scheduled_exams', 'Consulter ses examens programmés'),
  ('view_own_results', 'Consulter ses résultats'),
  ('select_exam_session', 'Sélectionner une session d''examen'),
  ('verify_candidates', 'Vérifier les candidats'),
  ('start_exam', 'Démarrer l''examen'),
  ('end_exam', 'Terminer l''examen');

insert into role_permissions (role_id, permission_id)
select 'national', id from permissions
where id in (
  'create_regional_direction', 'edit_regional_direction', 'delete_regional_direction',
  'view_all_exams', 'view_all_stats', 'view_all_etablissements', 'view_all_surveillants',
  'view_all_candidates', 'export_reports', 'manage_platform_settings'
);

insert into role_permissions (role_id, permission_id)
select 'regional', id from permissions
where id in (
  'create_etablissement', 'edit_etablissement', 'disable_etablissement',
  'create_surveillant_account', 'create_exam_session', 'assign_exam_session',
  'view_region_exams', 'view_region_candidates', 'view_region_results',
  'view_region_history', 'export_region_reports'
);

insert into role_permissions (role_id, permission_id)
select 'etablissement', id from permissions
where id in (
  'import_candidates_excel', 'view_own_candidates', 'view_own_scheduled_exams', 'view_own_results'
);

insert into role_permissions (role_id, permission_id)
select 'surveillant', id from permissions
where id in (
  'select_exam_session', 'verify_candidates', 'start_exam', 'end_exam'
);
