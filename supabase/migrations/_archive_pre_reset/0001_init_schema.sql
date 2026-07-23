-- Certif-App online platform — P1 foundations.
-- Schema per ~/.claude/plans/jiggly-hopping-cascade.md §1.1; RLS policies below
-- are a first pass implementing the principle described in §1.2/§5 — review
-- before any dashboard/kiosk code relies on them in production.
--
-- Run this once, in full, via the Supabase project's SQL Editor
-- (https://supabase.com/dashboard/project/pummdlglelbsviokubxw/sql/new).

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

create type user_role as enum ('national', 'regional', 'etablissement', 'surveillant');

create table regions (
  id uuid primary key default gen_random_uuid(),
  name text not null unique
);

create table etablissements (
  id uuid primary key default gen_random_uuid(),
  region_id uuid not null references regions(id),
  name text not null,
  login text not null unique,          -- identifiant fourni par la DR
  access_code_hash text,               -- code d'accès à usage unique (PBKDF2), null une fois activé
  activated_at timestamptz,
  created_by uuid,                     -- FK added below, once profiles exists
  created_at timestamptz not null default now()
);

create table profiles (
  id uuid primary key references auth.users(id),
  role user_role not null,
  region_id uuid references regions(id),
  etablissement_id uuid references etablissements(id),
  full_name text not null,
  created_at timestamptz not null default now()
);

alter table etablissements
  add constraint etablissements_created_by_fkey
  foreign key (created_by) references profiles(id);

create table exam_sessions (
  id uuid primary key default gen_random_uuid(),
  etablissement_id uuid not null references etablissements(id),
  exam_date date not null,
  start_time time not null,
  variant_mode text not null default 'alternate',  -- A/B, cf. PLAN.md §2
  status text not null default 'scheduled' check (status in ('scheduled', 'open', 'closed')),
  created_by uuid references profiles(id),         -- une DR
  created_at timestamptz not null default now()
);

create table stagiaires (
  id uuid primary key default gen_random_uuid(),
  etablissement_id uuid not null references etablissements(id),
  exam_session_id uuid references exam_sessions(id),
  first_name text not null,
  last_name text not null,
  cin text not null,
  birth_date date,
  phone text,
  import_batch_id uuid,
  created_at timestamptz not null default now(),
  unique (etablissement_id, cin)
);

create table stagiaire_imports (      -- audit de chaque upload Excel
  id uuid primary key default gen_random_uuid(),
  etablissement_id uuid not null references etablissements(id),
  exam_session_id uuid references exam_sessions(id),
  uploaded_by uuid references profiles(id),
  file_name text,
  row_count int,
  created_at timestamptz not null default now()
);

create table exam_attempts (          -- pont desktop <-> plateforme
  id uuid primary key default gen_random_uuid(),
  stagiaire_id uuid not null references stagiaires(id),
  exam_session_id uuid not null references exam_sessions(id),
  validated_by uuid references profiles(id),   -- surveillant
  validated_at timestamptz,
  desktop_session_uuid uuid,          -- correspond à sessions.id de la SQLite locale
  variant text,
  score_pct numeric,
  passed boolean,
  started_at timestamptz,
  ended_at timestamptz,
  synced_at timestamptz not null default now()
);

create table audit_log (
  id bigint generated always as identity primary key,
  actor uuid references profiles(id),
  etablissement_id uuid references etablissements(id),
  event text not null,
  detail jsonb,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 2. Helper functions (avoid recursive RLS lookups against profiles itself)
-- ---------------------------------------------------------------------------

create or replace function my_role() returns user_role
language sql stable security definer set search_path = public as $$
  select role from profiles where id = auth.uid();
$$;

create or replace function my_region_id() returns uuid
language sql stable security definer set search_path = public as $$
  select region_id from profiles where id = auth.uid();
$$;

create or replace function my_etablissement_id() returns uuid
language sql stable security definer set search_path = public as $$
  select etablissement_id from profiles where id = auth.uid();
$$;

-- ---------------------------------------------------------------------------
-- 3. Row Level Security
-- ---------------------------------------------------------------------------
-- Writes (create établissement/surveillant accounts, stagiaire import, etc.)
-- go through Edge Functions using the service-role key, which bypasses RLS —
-- so most policies below are read-scoped; only the desktop kiosk flow
-- (stagiaire import, exam_attempts) needs authenticated-role write policies.

alter table regions enable row level security;
alter table etablissements enable row level security;
alter table profiles enable row level security;
alter table exam_sessions enable row level security;
alter table stagiaires enable row level security;
alter table stagiaire_imports enable row level security;
alter table exam_attempts enable row level security;
alter table audit_log enable row level security;

-- regions: reference data, readable by any authenticated dashboard/kiosk user.
create policy regions_select_authenticated on regions
  for select using (auth.role() = 'authenticated');

-- profiles
create policy profiles_select_self on profiles
  for select using (id = auth.uid());

create policy profiles_select_national on profiles
  for select using (my_role() = 'national');

create policy profiles_select_regional on profiles
  for select using (my_role() = 'regional' and region_id = my_region_id());

create policy profiles_select_etablissement on profiles
  for select using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- etablissements
create policy etablissements_select_national on etablissements
  for select using (my_role() = 'national');

create policy etablissements_select_regional on etablissements
  for select using (my_role() = 'regional' and region_id = my_region_id());

create policy etablissements_select_self on etablissements
  for select using (my_role() = 'etablissement' and id = my_etablissement_id());

-- exam_sessions
create policy exam_sessions_select_national on exam_sessions
  for select using (my_role() = 'national');

create policy exam_sessions_select_regional on exam_sessions
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = exam_sessions.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy exam_sessions_select_etablissement on exam_sessions
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and etablissement_id = my_etablissement_id()
  );

-- stagiaires (kiosk reads these "as établissement" for the CIN check, §3.2)
create policy stagiaires_select_national on stagiaires
  for select using (my_role() = 'national');

create policy stagiaires_select_regional on stagiaires
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = stagiaires.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy stagiaires_select_etablissement on stagiaires
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and etablissement_id = my_etablissement_id()
  );

create policy stagiaires_insert_etablissement on stagiaires
  for insert with check (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

create policy stagiaires_update_etablissement on stagiaires
  for update using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- stagiaire_imports
create policy stagiaire_imports_select_national on stagiaire_imports
  for select using (my_role() = 'national');

create policy stagiaire_imports_select_regional on stagiaire_imports
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = stagiaire_imports.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy stagiaire_imports_select_etablissement on stagiaire_imports
  for select using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

create policy stagiaire_imports_insert_etablissement on stagiaire_imports
  for insert with check (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

-- exam_attempts (read via établissement/surveillant token; write is
-- surveillant-only, per §5 — the kiosk's établissement session cannot create
-- or edit validation rows).
create policy exam_attempts_select_national on exam_attempts
  for select using (my_role() = 'national');

create policy exam_attempts_select_regional on exam_attempts
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from exam_sessions s
      join etablissements e on e.id = s.etablissement_id
      where s.id = exam_attempts.exam_session_id and e.region_id = my_region_id()
    )
  );

create policy exam_attempts_select_etablissement on exam_attempts
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and exists (
      select 1 from exam_sessions s
      where s.id = exam_attempts.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

create policy exam_attempts_insert_surveillant on exam_attempts
  for insert with check (
    my_role() = 'surveillant'
    and exists (
      select 1 from exam_sessions s
      where s.id = exam_attempts.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

create policy exam_attempts_update_surveillant on exam_attempts
  for update using (
    my_role() = 'surveillant'
    and exists (
      select 1 from exam_sessions s
      where s.id = exam_attempts.exam_session_id and s.etablissement_id = my_etablissement_id()
    )
  );

-- audit_log
create policy audit_log_select_national on audit_log
  for select using (my_role() = 'national');

create policy audit_log_select_regional on audit_log
  for select using (
    my_role() = 'regional'
    and exists (
      select 1 from etablissements e
      where e.id = audit_log.etablissement_id and e.region_id = my_region_id()
    )
  );

create policy audit_log_select_etablissement on audit_log
  for select using (
    my_role() in ('etablissement', 'surveillant')
    and etablissement_id = my_etablissement_id()
  );
