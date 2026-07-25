-- Certif-App — adds DELETE on candidates for 'etablissement' (its own
-- candidates) and 'national' (any candidate), needed by the dashboard's
-- "Supprimer" action on the candidates table. 0001_full_schema.sql only ever
-- defined select/insert/update for candidates — no role could delete one at
-- all — and 0002_national_full_access.sql didn't add it either since there
-- was nothing to mirror at the time.
--
-- Run once, in full, via the Supabase project's SQL Editor, AFTER 0001 and
-- 0002. Do NOT run twice (policy names are not idempotent).

create policy candidates_delete_etablissement on candidates
  for delete using (my_role() = 'etablissement' and etablissement_id = my_etablissement_id());

create policy candidates_delete_national on candidates
  for delete using (my_role() = 'national');
