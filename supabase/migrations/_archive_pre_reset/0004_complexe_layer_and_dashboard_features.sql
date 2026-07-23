-- Certif-App online platform — 0004: Complexe de Formation layer + dashboard
-- features (établissement Excel import, PDF bilan support, incident reports,
-- session lifecycle, account activation).
--
-- Builds on 0001_init_schema.sql + 0003_rename_to_candidate_workflow.sql.
-- (0002_extend_schema.sql was an abandoned parallel draft written on the
-- pre-rename schema — never applied, superseded by 0003's rename. See 0003's
-- own header and web/dashboard/src/lib/database.types.ts. Ignored here.)
--
-- New hierarchy: regional (DR) -> complexe (CF) -> etablissement (ET) ->
-- surveillant (SV), with 'national' left untouched above 'regional' exactly
-- as it exists today. A "complexe" groups several établissements; DR now
-- creates Complexe accounts (not établissements directly — see the dropped
-- placeholder in RegionalDashboard.tsx), and a Complexe creates the
-- établissements under it. Régional data visibility (KPIs, exam_schedules,
-- candidates, audit_logs, ...) stays scoped by etablissements.region_id
-- exactly as in 0001 — that column is untouched, so none of 0001's or
-- 0003's *_select_regional policies need to change.
--
-- The desktop kiosk (excel_cert_app/app/supabase_service/) reads/writes
-- candidates.first_name/last_name/cin/birth_date/sexe/filiere/groupe,
-- exam_schedules.status IN ('scheduled','open',...)/mos_version/exam_date/
-- start_time, and exam_sessions.* (started/terminated lifecycle) by exact
-- name and value today. None of those are renamed or removed below — only
-- new nullable columns and new allowed status values are added.
--
-- Run this once, in full, via the Supabase project's SQL Editor
-- (https://supabase.com/dashboard/project/pummdlglelbsviokubxw/sql/new),
-- AFTER 0001 and 0003 have both already been applied.
--
-- IMPORTANT — run in two separate pastes. Postgres does not allow a brand
-- new enum value to be used by other statements in the same transaction
-- block it was added in. Run "STEP 1" alone, wait for it to say Success,
-- THEN run everything from "STEP 2" onward as a second paste.

-- ---------------------------------------------------------------------------
-- STEP 1 — new role value (must commit before it is used below)
-- ---------------------------------------------------------------------------

alter type user_role add value if not exists 'complexe';

-- ############################################################################
-- ###  STOP HERE — run STEP 1 above by itself first, confirm it succeeded,  ###
-- ###  then run everything below as a second paste.                        ###
-- ############################################################################

-- ---------------------------------------------------------------------------
-- STEP 2 — new tables
-- ---------------------------------------------------------------------------

-- Complexe de Formation: groups several établissements under one DR region.
create table if not exists complexes (
  id uuid primary key default gen_random_uuid(),
  region_id uuid not null references regions(id),
  name text not null,
  created_by uuid references profiles(id),
  created_at timestamptz not null default now()
);

alter table etablissements add column if not exists complexe_id uuid references complexes(id);

-- profiles: link CF accounts to their complexe, and give every account an
-- activation toggle (today only etablissements.activated_at existed, and it
-- was never wired to anything — a single flag on profiles covers all roles
-- uniformly and is enforced centrally below via the my_*() helpers).
alter table profiles add column if not exists complexe_id uuid references complexes(id);
alter table profiles add column if not exists is_active boolean not null default true;
-- Display-only copy of the auth.users email set at account creation by the
-- manage-user Edge Function (service role) — dashboards running under the
-- anon key have no other way to show "which email does this account log in
-- with" since RLS can't expose auth.users. Not used for authentication.
alter table profiles add column if not exists login text;

-- Excel import audit trail with a per-row report (nb_inseres/doublons/erreurs
-- + errors_json). Richer than 0001's stagiaire_imports, which stays in place
-- untouched but is no longer written by the dashboard's import flow.
create table if not exists excel_imports (
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

-- candidates.import_batch_id already exists (bare uuid, 0001) but was never
-- constrained to a real table — point it at excel_imports now that one
-- exists. excel_imports is brand new (just created above, zero rows), so any
-- import_batch_id already sitting on a candidates row today is necessarily
-- orphaned relative to it (the pre-0004 dashboard code generated these
-- client-side via crypto.randomUUID() against the old, now-unused
-- stagiaire_imports table) — clear those first or the ADD CONSTRAINT below
-- fails outright on any établissement that already tested the old import flow.
update candidates set import_batch_id = null where import_batch_id is not null;

alter table candidates add constraint candidates_import_batch_id_fkey
  foreign key (import_batch_id) references excel_imports(id);

-- Per-task grading breakdown for the PDF bilan (§4.3) — nothing in 0001/0003
-- carries this today; the desktop kiosk's grading engine (app/grading/)
-- currently only produces it in the local resultats.xlsx export. Nullable
-- and additive: the kiosk does not need to change to keep working, the PDF
-- bilan simply omits the per-task table until a future kiosk change starts
-- populating this column via exam_sessions.py's finish().
alter table exam_sessions add column if not exists task_results jsonb;

create table if not exists incident_reports (
  id uuid primary key default gen_random_uuid(),
  type_incident text,
  description text not null,
  exam_schedule_id uuid references exam_schedules(id),
  reported_by uuid references profiles(id),
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- STEP 3 — candidates: remaining Excel columns (30-column import spec)
-- ---------------------------------------------------------------------------
-- cin/first_name(Prenom)/last_name(Nom)/birth_date/phone/sexe/filiere/groupe/
-- photo_path already exist (0001/0003) and are read by name by the desktop
-- kiosk — not touched. Everything else the import spec needs is new below.

alter table candidates add column if not exists nom_arabe text;
alter table candidates add column if not exists prenom_arabe text;
alter table candidates add column if not exists prenom2 text;
alter table candidates add column if not exists lieu_naissance text;
alter table candidates add column if not exists matricule_etudiant text;
alter table candidates add column if not exists diplome text;
alter table candidates add column if not exists code_diplome text;
alter table candidates add column if not exists libelle_long text;
alter table candidates add column if not exists principale text;
alter table candidates add column if not exists code text;
alter table candidates add column if not exists codediplome1 text;
alter table candidates add column if not exists niveau_scolaire text;
alter table candidates add column if not exists annee_etude text;
alter table candidates add column if not exists etudiant_actif boolean;
alter table candidates add column if not exists etudiant_payant boolean;
alter table candidates add column if not exists regime_inscription text;
alter table candidates add column if not exists date_inscription date;
alter table candidates add column if not exists date_dossier_complet date;
alter table candidates add column if not exists motif_admission text;
alter table candidates add column if not exists site text;
alter table candidates add column if not exists n_tel_tuteur text;
alter table candidates add column if not exists adresse text;
alter table candidates add column if not exists nationalite text;
alter table candidates add column if not exists id_inscription_session text;

-- ---------------------------------------------------------------------------
-- STEP 4 — exam_schedules: richer status lifecycle + seat count
-- ---------------------------------------------------------------------------
-- 'scheduled' and 'open' are read by exact value by the desktop kiosk
-- (candidates.py gates lookup on status = 'open') — kept as-is. Adding
-- 'in_progress' and 'cancelled' for the DR calendar's full lifecycle
-- (planifié/ouvert/en_cours/terminé/annulé — 'closed' already covers
-- terminé, no rename needed).
--
-- Note on the constraint name: this table was called `exam_sessions` in
-- 0001, so Postgres auto-named its inline status check
-- `exam_sessions_status_check` — table renames (0003) don't rename existing
-- constraints. Do NOT confuse this with the *different* constraint of the
-- same auto-generated name that 0003 explicitly created on the *other*
-- table now also called `exam_sessions` (the per-candidate attempt, values
-- 'started'/'terminated') — that one is untouched by this migration.

alter table exam_schedules add column if not exists nb_postes integer;

alter table exam_schedules drop constraint if exists exam_sessions_status_check;
alter table exam_schedules add constraint exam_schedules_status_check
  check (status in ('scheduled', 'open', 'in_progress', 'closed', 'cancelled'));

-- Missing from 0001: DR needs to be able to actually create/edit sessions
-- from the dashboard (RegionalDashboard.tsx already calls .insert() on
-- exam_schedules) — 0001 only ever granted SELECT on this table.
create policy exam_schedules_insert_regional on exam_schedules
  for insert with check (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy exam_schedules_update_regional on exam_schedules
  for update using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy exam_schedules_delete_regional on exam_schedules
  for delete using (
    my_role() = 'regional'
    and status = 'scheduled'
    and exists (
      select 1 from etablissements e
      where e.id = exam_schedules.etablissement_id and e.region_id = my_region_id()
    )
  );

-- ---------------------------------------------------------------------------
-- STEP 5 — helper functions: add my_complexe_id(), and make every helper
-- fail closed for a deactivated account (single choke point instead of
-- adding `is_active` checks to every policy below).
-- ---------------------------------------------------------------------------

create or replace function my_role() returns user_role
language sql stable security definer set search_path = public as $$
  select role from profiles where id = auth.uid() and is_active;
$$;

create or replace function my_region_id() returns uuid
language sql stable security definer set search_path = public as $$
  select region_id from profiles where id = auth.uid() and is_active;
$$;

create or replace function my_etablissement_id() returns uuid
language sql stable security definer set search_path = public as $$
  select etablissement_id from profiles where id = auth.uid() and is_active;
$$;

create or replace function my_complexe_id() returns uuid
language sql stable security definer set search_path = public as $$
  select complexe_id from profiles where id = auth.uid() and is_active;
$$;

-- ---------------------------------------------------------------------------
-- STEP 6 — Row Level Security
-- ---------------------------------------------------------------------------

alter table complexes enable row level security;
alter table excel_imports enable row level security;
alter table incident_reports enable row level security;

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

-- etablissements: add the 'complexe' branch (national/regional/self from
-- 0001 are untouched — regional visibility stays region_id-based).
create policy etablissements_select_complexe on etablissements
  for select using (my_role() = 'complexe' and complexe_id = my_complexe_id());

-- etablissements: 0001's etablissements_select_self only covers role
-- 'etablissement', not 'surveillant' — meaning a surveillant querying their
-- own etablissements row (e.g. via the complexes_select_etablissement
-- subquery just below) got zero rows back under RLS. Every other
-- etablissement-scoped policy in this project (exam_schedules, exam_sessions,
-- incident_reports, ...) already includes 'surveillant' alongside
-- 'etablissement' — this was a gap, not an intentional restriction.
create policy etablissements_select_surveillant on etablissements
  for select using (my_role() = 'surveillant' and id = my_etablissement_id());

-- profiles: regional profiles are scoped by region_id (0001), but a
-- complexe's profile carries complexe_id instead (no region_id — its region
-- is only reachable via complexes.region_id) — without this, DR's "manage
-- complexes" screen couldn't see/toggle CF accounts at all.
create policy profiles_select_regional_complexe on profiles
  for select using (
    my_role() = 'regional'
    and complexe_id in (select id from complexes where region_id = my_region_id())
  );

-- profiles: add the 'complexe' branch — sees its own row plus every
-- etablissement/surveillant profile under its complexe. Mirrors the shape
-- of 0001's profiles_select_etablissement.
create policy profiles_select_complexe on profiles
  for select using (
    my_role() = 'complexe'
    and (
      id = auth.uid()
      or etablissement_id in (select id from etablissements where complexe_id = my_complexe_id())
    )
  );

-- exam_schedules: add the 'complexe' branch alongside 0001's
-- national/regional/etablissement SELECT policies.
create policy exam_schedules_select_complexe on exam_schedules
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from etablissements e
      where e.id = exam_schedules.etablissement_id and e.complexe_id = my_complexe_id()
    )
  );

-- candidates: add the 'complexe' branch (read-only — import stays ET-only).
create policy candidates_select_complexe on candidates
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from etablissements e
      where e.id = candidates.etablissement_id and e.complexe_id = my_complexe_id()
    )
  );

-- exam_sessions (candidate attempts): add the 'complexe' branch.
create policy exam_sessions_select_complexe on exam_sessions
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from exam_schedules sch
      join etablissements e on e.id = sch.etablissement_id
      where sch.id = exam_sessions.exam_schedule_id and e.complexe_id = my_complexe_id()
    )
  );

-- audit_logs: add the 'complexe' branch.
create policy audit_logs_select_complexe on audit_logs
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from etablissements e
      where e.id = audit_logs.etablissement_id and e.complexe_id = my_complexe_id()
    )
  );

-- excel_imports
create policy excel_imports_select_national on excel_imports
  for select using (my_role() = 'national');

create policy excel_imports_select_regional on excel_imports
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = excel_imports.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy excel_imports_select_complexe on excel_imports
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from etablissements e
      where e.id = excel_imports.etablissement_id and e.complexe_id = my_complexe_id()
    )
  );

create policy excel_imports_select_etablissement on excel_imports
  for select using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

create policy excel_imports_insert_etablissement on excel_imports
  for insert with check (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

create policy excel_imports_update_etablissement on excel_imports
  for update using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- incident_reports
create policy incident_reports_select_national on incident_reports
  for select using (my_role() = 'national');

create policy incident_reports_select_regional on incident_reports
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      join exam_schedules sch on sch.etablissement_id = e.id
      where sch.id = incident_reports.exam_schedule_id and e.region_id = my_region_id()
    )
  );

create policy incident_reports_select_complexe on incident_reports
  for select using (
    my_role() = 'complexe'
    and exists (
      select 1 from etablissements e
      join exam_schedules sch on sch.etablissement_id = e.id
      where sch.id = incident_reports.exam_schedule_id and e.complexe_id = my_complexe_id()
    )
  );

create policy incident_reports_select_etablissement on incident_reports
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and exists (
      select 1 from exam_schedules sch
      where sch.id = incident_reports.exam_schedule_id and sch.etablissement_id = my_etablissement_id()
    )
  );

create policy incident_reports_insert_surveillant on incident_reports
  for insert with check (
    my_role() = 'surveillant'
    and reported_by = auth.uid()
    and exists (
      select 1 from exam_schedules sch
      where sch.id = incident_reports.exam_schedule_id and sch.etablissement_id = my_etablissement_id()
    )
  );

-- Note: surveillant already has SELECT on exam_schedules for its own
-- etablissement_id via 0001's `exam_sessions_select_etablissement` policy
-- (created before the 0003 rename, so it kept that name but now applies to
-- exam_schedules) — its predicate already reads
-- `my_role() in ('etablissement', 'surveillant')`, nothing to add here.

-- ---------------------------------------------------------------------------
-- STEP 7 — Realtime
-- ---------------------------------------------------------------------------
-- CF's session monitor and SV's dashboard subscribe to these via
-- postgres_changes (see src/hooks/useRealtimeTable.ts) — Realtime only
-- broadcasts a table's changes once it's in this publication (equivalent to
-- the Database -> Replication toggle in the dashboard UI). RLS still
-- applies per-subscriber on top of this.

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
