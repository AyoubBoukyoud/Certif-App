-- Certif-App online platform — full schema, consolidated baseline.
-- Part 2/2 of the reset — run 0000_drop_all.sql FIRST, then this file.
--
-- Replaces the old 0001 -> 0004 migration chain (archived under
-- supabase/migrations/_archive_pre_reset/ for reference — do not run those
-- anymore). This single file creates the whole schema directly under its
-- final names, since the live project is being reset from scratch rather
-- than migrated forward step by step.
--
-- Hierarchy: national (untouched top tier) -> regional (Direction
-- Régionale) -> complexe (Complexe de Formation) -> etablissement -> the
-- surveillant role (kiosk validation login, no standing dashboard account
-- required). Candidates have no login — identified by CIN at the kiosk.
--
-- IMPORTANT — this schema is a hard dependency of the already-written
-- desktop kiosk (excel_cert_app/app/supabase_service/). It reads/writes, by
-- exact name and value:
--   candidates.first_name / last_name / cin / birth_date / sexe / filiere /
--     groupe / photo_path / etablissement_id / exam_schedule_id
--   exam_schedules.status ('scheduled' / 'open' gate the kiosk's candidate
--     lookup) / mos_version / exam_date / start_time
--   exam_sessions.* — candidate_id, exam_schedule_id, validated_by,
--     validated_at, desktop_session_uuid, workstation, hostname, ip_local,
--     started_at, ended_at, score_pct, passed, incidents, technical_logs,
--     status ('started' / 'terminated')
--   profiles.role / full_name / etablissement_id
-- If you ever hand-edit this file, keep those exact — the kiosk is not
-- being changed alongside this reset.
--
-- Run this once, in full, via the Supabase project's SQL Editor
-- (https://supabase.com/dashboard/project/pummdlglelbsviokubxw/sql/new),
-- on the `public` schema, AFTER 0000_drop_all.sql. It does NOT touch
-- `auth.users` — if you already created test accounts and want a truly
-- clean slate, delete them separately under Authentication -> Users, or
-- reuse them (their emails will just need a fresh profiles/entity row,
-- which this file provides).

-- ============================================================================
-- STEP 1 — extensions & enum
-- ============================================================================

create extension if not exists pgcrypto;

create type user_role as enum ('national', 'regional', 'complexe', 'etablissement', 'surveillant');

-- ============================================================================
-- STEP 2 — tables
-- ============================================================================

create table regions (
  id uuid primary key default gen_random_uuid(),
  name text not null unique
);

create table complexes (
  id uuid primary key default gen_random_uuid(),
  region_id uuid not null references regions(id),
  name text not null,
  created_by uuid, -- FK to profiles added after profiles exists (circular otherwise)
  created_at timestamptz not null default now()
);

create table etablissements (
  id uuid primary key default gen_random_uuid(),
  region_id uuid not null references regions(id),
  complexe_id uuid references complexes(id),
  name text not null,
  login text not null unique, -- display copy of the account's email, set by manage-user
  created_by uuid, -- FK to profiles added after profiles exists
  created_at timestamptz not null default now()
);

create table profiles (
  id uuid primary key references auth.users(id),
  role user_role not null,
  region_id uuid references regions(id),
  complexe_id uuid references complexes(id),
  etablissement_id uuid references etablissements(id),
  full_name text not null,
  login text, -- display copy of the account's email, set by manage-user
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

alter table complexes
  add constraint complexes_created_by_fkey foreign key (created_by) references profiles(id);
alter table etablissements
  add constraint etablissements_created_by_fkey foreign key (created_by) references profiles(id);

create table exam_schedules (
  id uuid primary key default gen_random_uuid(),
  etablissement_id uuid not null references etablissements(id),
  exam_date date not null,
  start_time time not null,
  variant_mode text not null default 'alternate', -- A/B, cf. PLAN.md §2
  status text not null default 'scheduled'
    check (status in ('scheduled', 'open', 'in_progress', 'closed', 'cancelled')),
  room text,
  duration_minutes int,
  mos_version text,
  nb_postes integer,
  created_by uuid references profiles(id),
  created_at timestamptz not null default now()
);

create table excel_imports (
  id uuid primary key default gen_random_uuid(),
  etablissement_id uuid not null references etablissements(id),
  exam_schedule_id uuid references exam_schedules(id),
  nom_fichier text,
  nb_lignes integer not null default 0,
  nb_inseres integer not null default 0,
  nb_doublons integer not null default 0,
  nb_erreurs integer not null default 0,
  statut text not null default 'en_cours' check (statut in ('en_cours', 'termine', 'erreur')),
  errors_json jsonb not null default '[]',
  created_by uuid references profiles(id),
  created_at timestamptz not null default now()
);

-- 30-column Excel import spec. first_name/last_name/cin/birth_date/phone/
-- sexe/filiere/groupe/photo_path are the columns the desktop kiosk reads by
-- exact name — keep those if this file is ever hand-edited.
create table candidates (
  id uuid primary key default gen_random_uuid(),
  etablissement_id uuid not null references etablissements(id),
  exam_schedule_id uuid references exam_schedules(id),
  first_name text not null,
  last_name text not null,
  cin text not null,
  birth_date date,
  phone text,
  sexe text,
  filiere text,
  groupe text,
  photo_path text,
  nom_arabe text,
  prenom_arabe text,
  prenom2 text,
  lieu_naissance text,
  matricule_etudiant text,
  diplome text,
  code_diplome text,
  libelle_long text,
  principale text,
  code text,
  codediplome1 text,
  niveau_scolaire text,
  annee_etude text,
  etudiant_actif boolean,
  etudiant_payant boolean,
  regime_inscription text,
  date_inscription date,
  date_dossier_complet date,
  motif_admission text,
  site text,
  n_tel_tuteur text,
  adresse text,
  nationalite text,
  id_inscription_session text,
  import_batch_id uuid references excel_imports(id),
  created_at timestamptz not null default now(),
  unique (etablissement_id, cin)
);

-- Per-candidate attempt — bridges the desktop kiosk to the platform.
-- validated_by / workstation / hostname / ip_local / started_at / ended_at /
-- score_pct / passed / incidents / technical_logs / status are written by
-- the kiosk (app/supabase_service/exam_sessions.py) — keep exact.
create table exam_sessions (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references candidates(id),
  exam_schedule_id uuid not null references exam_schedules(id),
  validated_by uuid references profiles(id), -- surveillant
  validated_at timestamptz,
  desktop_session_uuid uuid, -- corresponds to the local SQLite sessions.id
  variant text,
  score_pct numeric,
  passed boolean,
  started_at timestamptz,
  ended_at timestamptz,
  workstation text,
  hostname text,
  ip_local text,
  incidents jsonb,
  technical_logs jsonb,
  task_results jsonb, -- per-task PDF-bilan breakdown; not yet sent by the kiosk
  status text not null default 'started' check (status in ('started', 'terminated')),
  synced_at timestamptz not null default now()
);

create table incident_reports (
  id uuid primary key default gen_random_uuid(),
  type_incident text,
  description text not null,
  exam_schedule_id uuid references exam_schedules(id),
  reported_by uuid references profiles(id),
  created_at timestamptz not null default now()
);

create table audit_logs (
  id bigint generated always as identity primary key,
  actor uuid references profiles(id),
  candidate_id uuid references candidates(id),
  etablissement_id uuid references etablissements(id),
  event text not null,
  hostname text,
  result text,
  message text,
  app_version text,
  detail jsonb,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- STEP 3 — helper functions (avoid recursive RLS lookups against profiles
-- itself; also the single choke point that makes a deactivated account
-- (is_active = false) fail every policy below at once).
-- ============================================================================

create or replace function my_role() returns user_role
language sql stable security definer set search_path = public as $$
  select role from profiles where id = auth.uid() and is_active;
$$;

create or replace function my_region_id() returns uuid
language sql stable security definer set search_path = public as $$
  select region_id from profiles where id = auth.uid() and is_active;
$$;

create or replace function my_complexe_id() returns uuid
language sql stable security definer set search_path = public as $$
  select complexe_id from profiles where id = auth.uid() and is_active;
$$;

create or replace function my_etablissement_id() returns uuid
language sql stable security definer set search_path = public as $$
  select etablissement_id from profiles where id = auth.uid() and is_active;
$$;

-- ============================================================================
-- STEP 4 — Row Level Security
-- ============================================================================
-- Account creation/management (create, activate/deactivate, reset password,
-- delete) goes through the manage-user Edge Function (service role, bypasses
-- RLS) — see supabase/functions/manage-user/index.ts. Policies below are
-- read-scoped except where the kiosk/dashboard itself needs to write
-- directly (candidates import, exam_sessions, incident_reports).

alter table regions enable row level security;
alter table complexes enable row level security;
alter table etablissements enable row level security;
alter table profiles enable row level security;
alter table exam_schedules enable row level security;
alter table excel_imports enable row level security;
alter table candidates enable row level security;
alter table exam_sessions enable row level security;
alter table incident_reports enable row level security;
alter table audit_logs enable row level security;

-- regions: reference data, readable by any authenticated dashboard/kiosk user.
create policy regions_select_authenticated on regions
  for select using (auth.role() = 'authenticated');

-- complexes
create policy complexes_select_national on complexes
  for select using (my_role() = 'national');
create policy complexes_select_regional on complexes
  for select using (my_role() = 'regional' and region_id = my_region_id());
create policy complexes_select_self on complexes
  for select using (my_role() = 'complexe' and id = my_complexe_id());
create policy complexes_select_etablissement on complexes
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and id = (select complexe_id from etablissements where id = my_etablissement_id())
  );

-- etablissements
create policy etablissements_select_national on etablissements
  for select using (my_role() = 'national');
create policy etablissements_select_regional on etablissements
  for select using (my_role() = 'regional' and region_id = my_region_id());
create policy etablissements_select_complexe on etablissements
  for select using (my_role() = 'complexe' and complexe_id = my_complexe_id());
create policy etablissements_select_self on etablissements
  for select using (my_role() = 'etablissement' and id = my_etablissement_id());
create policy etablissements_select_surveillant on etablissements
  for select using (my_role() = 'surveillant' and id = my_etablissement_id());

-- profiles
create policy profiles_select_self on profiles
  for select using (id = auth.uid());
create policy profiles_select_national on profiles
  for select using (my_role() = 'national');
create policy profiles_select_regional on profiles
  for select using (my_role() = 'regional' and region_id = my_region_id());
create policy profiles_select_regional_complexe on profiles
  for select using (
    my_role() = 'regional' and complexe_id in (select id from complexes where region_id = my_region_id())
  );
create policy profiles_select_complexe on profiles
  for select using (
    my_role() = 'complexe'
    and etablissement_id in (select id from etablissements where complexe_id = my_complexe_id())
  );
create policy profiles_select_etablissement on profiles
  for select using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- exam_schedules
create policy exam_schedules_select_national on exam_schedules
  for select using (my_role() = 'national');
create policy exam_schedules_select_regional on exam_schedules
  for select using (
    my_role() = 'regional'
    and exists (select 1 from etablissements e where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id())
  );
create policy exam_schedules_select_complexe on exam_schedules
  for select using (
    my_role() = 'complexe'
    and exists (select 1 from etablissements e where e.id = exam_schedules.etablissement_id and e.complexe_id = my_complexe_id())
  );
create policy exam_schedules_select_etablissement on exam_schedules
  for select using (
    my_role() in ('etablissement', 'surveillant') and etablissement_id = my_etablissement_id()
  );
create policy exam_schedules_insert_regional on exam_schedules
  for insert with check (
    my_role() = 'regional'
    and exists (select 1 from etablissements e where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id())
  );
create policy exam_schedules_update_regional on exam_schedules
  for update using (
    my_role() = 'regional'
    and exists (select 1 from etablissements e where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id())
  );
create policy exam_schedules_delete_regional on exam_schedules
  for delete using (
    my_role() = 'regional' and status = 'scheduled'
    and exists (select 1 from etablissements e where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id())
  );

-- excel_imports
create policy excel_imports_select_national on excel_imports
  for select using (my_role() = 'national');
create policy excel_imports_select_regional on excel_imports
  for select using (
    my_role() = 'regional'
    and exists (select 1 from etablissements e where e.id = excel_imports.etablissement_id and e.region_id = my_region_id())
  );
create policy excel_imports_select_complexe on excel_imports
  for select using (
    my_role() = 'complexe'
    and exists (select 1 from etablissements e where e.id = excel_imports.etablissement_id and e.complexe_id = my_complexe_id())
  );
create policy excel_imports_select_etablissement on excel_imports
  for select using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());
create policy excel_imports_insert_etablissement on excel_imports
  for insert with check (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());
create policy excel_imports_update_etablissement on excel_imports
  for update using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- candidates (kiosk reads these "as établissement" for the CIN check)
create policy candidates_select_national on candidates
  for select using (my_role() = 'national');
create policy candidates_select_regional on candidates
  for select using (
    my_role() = 'regional'
    and exists (select 1 from etablissements e where e.id = candidates.etablissement_id and e.region_id = my_region_id())
  );
create policy candidates_select_complexe on candidates
  for select using (
    my_role() = 'complexe'
    and exists (select 1 from etablissements e where e.id = candidates.etablissement_id and e.complexe_id = my_complexe_id())
  );
create policy candidates_select_etablissement on candidates
  for select using (
    my_role() in ('etablissement', 'surveillant') and etablissement_id = my_etablissement_id()
  );
create policy candidates_insert_etablissement on candidates
  for insert with check (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());
create policy candidates_update_etablissement on candidates
  for update using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- exam_sessions (candidate attempts; write is surveillant-only — the
-- kiosk's établissement session never creates or edits validation rows)
create policy exam_sessions_select_national on exam_sessions
  for select using (my_role() = 'national');
create policy exam_sessions_select_regional on exam_sessions
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from exam_schedules sch join etablissements e on e.id = sch.etablissement_id
      where sch.id = exam_sessions.exam_schedule_id and e.region_id = my_region_id()
    )
  );
create policy exam_sessions_select_complexe on exam_sessions
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from exam_schedules sch join etablissements e on e.id = sch.etablissement_id
      where sch.id = exam_sessions.exam_schedule_id and e.complexe_id = my_complexe_id()
    )
  );
create policy exam_sessions_select_etablissement on exam_sessions
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and exists (select 1 from exam_schedules sch where sch.id = exam_sessions.exam_schedule_id and sch.etablissement_id = my_etablissement_id())
  );
create policy exam_sessions_insert_surveillant on exam_sessions
  for insert with check (
    my_role() = 'surveillant'
    and exists (select 1 from exam_schedules sch where sch.id = exam_sessions.exam_schedule_id and sch.etablissement_id = my_etablissement_id())
  );
create policy exam_sessions_update_surveillant on exam_sessions
  for update using (
    my_role() = 'surveillant'
    and exists (select 1 from exam_schedules sch where sch.id = exam_sessions.exam_schedule_id and sch.etablissement_id = my_etablissement_id())
  );

-- incident_reports
create policy incident_reports_select_national on incident_reports
  for select using (my_role() = 'national');
create policy incident_reports_select_regional on incident_reports
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e join exam_schedules sch on sch.etablissement_id = e.id
      where sch.id = incident_reports.exam_schedule_id and e.region_id = my_region_id()
    )
  );
create policy incident_reports_select_complexe on incident_reports
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from etablissements e join exam_schedules sch on sch.etablissement_id = e.id
      where sch.id = incident_reports.exam_schedule_id and e.complexe_id = my_complexe_id()
    )
  );
create policy incident_reports_select_etablissement on incident_reports
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and exists (select 1 from exam_schedules sch where sch.id = incident_reports.exam_schedule_id and sch.etablissement_id = my_etablissement_id())
  );
create policy incident_reports_insert_surveillant on incident_reports
  for insert with check (
    my_role() = 'surveillant' and reported_by = auth.uid()
    and exists (select 1 from exam_schedules sch where sch.id = incident_reports.exam_schedule_id and sch.etablissement_id = my_etablissement_id())
  );

-- audit_logs
create policy audit_logs_select_national on audit_logs
  for select using (my_role() = 'national');
create policy audit_logs_select_regional on audit_logs
  for select using (
    my_role() = 'regional'
    and exists (select 1 from etablissements e where e.id = audit_logs.etablissement_id and e.region_id = my_region_id())
  );
create policy audit_logs_select_complexe on audit_logs
  for select using (
    my_role() = 'complexe'
    and exists (select 1 from etablissements e where e.id = audit_logs.etablissement_id and e.complexe_id = my_complexe_id())
  );
create policy audit_logs_select_etablissement on audit_logs
  for select using (
    my_role() in ('etablissement', 'surveillant') and etablissement_id = my_etablissement_id()
  );
create policy audit_logs_insert_etablissement on audit_logs
  for insert with check (
    my_role() = 'etablissement' and (etablissement_id is null or etablissement_id = my_etablissement_id())
  );

-- ============================================================================
-- STEP 5 — Realtime (CF's session monitor, SV's dashboard)
-- ============================================================================

do $$
declare
  t text;
begin
  foreach t in array array['exam_schedules', 'exam_sessions', 'incident_reports'] loop
    if not exists (
      select 1 from pg_publication_tables
      where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t
    ) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

-- ============================================================================
-- STEP 6 — seed reference data + first account
-- ============================================================================
-- regions has no default rows and profiles/complexes/etablissements all
-- need at least one to bootstrap into. Uncomment and edit, or create your
-- first region + national/regional account by hand after this script runs
-- (a 'national'/'regional' profile can't be created via manage-user — it
-- only handles regional->complexe->etablissement->surveillant — so the very
-- first account has to be inserted directly, same as before this reset).
--
-- insert into regions (name) values ('Votre région');
--
-- Then, after creating the auth user (Dashboard -> Authentication -> Add
-- user, or auth.admin.createUser), link it:
-- insert into profiles (id, role, region_id, full_name, login, is_active)
-- values ('<auth-user-uuid>', 'regional', '<region-id-from-above>', 'Nom Prénom', '<email>', true);
