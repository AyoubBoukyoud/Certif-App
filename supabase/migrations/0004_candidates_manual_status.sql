-- Certif-App — adds a manual, dashboard-editable status override on
-- candidates. Until now a candidate's status badge (Validé / En cours / En
-- attente) was always derived from their exam_sessions attempts, with no way
-- to set it by hand (e.g. to mark a candidate exempted or validated outside
-- the kiosk flow). NULL keeps the old derived-from-exam_sessions behavior;
-- a non-null value overrides it.
--
-- Run once, in full, via the Supabase project's SQL Editor, AFTER 0001-0003.
-- Do NOT run twice (column/policy additions are not idempotent).

alter table candidates
  add column status text check (status in ('valide', 'en_cours', 'en_attente'));
