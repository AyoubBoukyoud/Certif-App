-- Certif-App — kiosk public RPCs.
--
-- Context: the desktop kiosk no longer pairs to an établissement account
-- (removed — see excel_cert_app/app/supabase_service/, no more pairing.py /
-- sign_in_kiosk). Établissement scoping for a poste is now derived
-- implicitly from whichever candidate's CIN is looked up, and confirmed by
-- the surveillant's own login at Écran 3 (their `profiles.etablissement_id`
-- must match the candidate's). Without a poste-level session, ordinary RLS
-- (etablissement_id = my_etablissement_id()) blocks every read/write the
-- kiosk needs before a surveillant is authenticated — these two
-- `security definer` functions are the deliberately narrow exceptions:
-- both take only the exact inputs the kiosk already has (a CIN, or audit
-- fields), and are granted to `anon` explicitly here.
--
-- Run this once, in full, via the Supabase project's SQL Editor, after
-- 0001_full_schema.sql.

-- ============================================================================
-- lookup_candidate_by_cin — Écran 2 (Identification du candidat).
-- Mirrors the filtering that used to live in candidates.py + exam_sessions.py
-- (cin match, exam_schedule open + dated today) but without requiring an
-- established établissement session first. Multiple attempts per candidate
-- are allowed on purpose (product decision) — this does not check or report
-- any prior exam_sessions row, unlike the first version of this function.
-- ============================================================================

-- Postgres refuses `create or replace` when a table function's column list
-- changes shape — drop first so re-running this file always lands cleanly,
-- whether or not the previous (already_attempted-reporting) version was
-- ever applied.
drop function if exists public.lookup_candidate_by_cin(text);

create function public.lookup_candidate_by_cin(p_cin text)
returns table (
  id uuid,
  first_name text,
  last_name text,
  cin text,
  birth_date date,
  sexe text,
  filiere text,
  groupe text,
  photo_path text,
  etablissement_id uuid,
  etablissement_name text,
  region_name text,
  exam_schedule_id uuid,
  mos_version text,
  exam_date date,
  start_time time
)
language sql
stable
security definer
set search_path = public
as $$
  select
    c.id, c.first_name, c.last_name, c.cin, c.birth_date, c.sexe, c.filiere,
    c.groupe, c.photo_path, c.etablissement_id, e.name, r.name,
    c.exam_schedule_id, s.mos_version, s.exam_date, s.start_time
  from candidates c
  join etablissements e on e.id = c.etablissement_id
  left join regions r on r.id = e.region_id
  join exam_schedules s on s.id = c.exam_schedule_id
  where c.cin = p_cin
    and s.status = 'open'
    and s.exam_date = current_date
  limit 1;
$$;

grant execute on function public.lookup_candidate_by_cin(text) to anon, authenticated;

-- ============================================================================
-- log_kiosk_event — mirrors AppController._remote_audit into audit_logs
-- before any candidate/surveillant session exists (system_check,
-- excel_crash, escape_attempt at Écran 1). Same shape as the direct table
-- insert it replaces; actor/candidate_id/etablissement_id are simply null
-- when not yet known.
-- ============================================================================

create or replace function public.log_kiosk_event(
  p_event text,
  p_hostname text default null,
  p_result text default 'ok',
  p_message text default '',
  p_app_version text default null,
  p_candidate_id uuid default null,
  p_etablissement_id uuid default null
) returns void
language sql
security definer
set search_path = public
as $$
  insert into audit_logs (event, hostname, result, message, app_version, candidate_id, etablissement_id)
  values (p_event, p_hostname, p_result, p_message, p_app_version, p_candidate_id, p_etablissement_id);
$$;

grant execute on function public.log_kiosk_event(text, text, text, text, text, uuid, uuid) to anon, authenticated;
