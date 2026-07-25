-- Roaming surveillant support: a `surveillant` profile with
-- `etablissement_id is null` now means "all établissements" instead of
-- belonging to none. Every policy that used to gate a surveillant on
-- `etablissement_id = my_etablissement_id()` is rewritten through the new
-- `scoped_to_etablissement()` helper so a null etablissement_id passes for
-- every row instead of matching none (a plain equality against NULL is
-- always false, which is why this can't be done in-place without rewriting
-- the policies).

create or replace function scoped_to_etablissement(target uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select
    (my_role() = 'etablissement' and target = my_etablissement_id())
    or (my_role() = 'surveillant' and (my_etablissement_id() is null or target = my_etablissement_id()));
$$;

-- etablissements
drop policy if exists etablissements_select_surveillant on etablissements;
create policy etablissements_select_surveillant on etablissements
  for select using (my_role() = 'surveillant' and (my_etablissement_id() is null or id = my_etablissement_id()));

-- complexes: split the combined etablissement+surveillant policy so the
-- surveillant half can special-case "roaming" (etablissement one is unchanged).
drop policy if exists complexes_select_etablissement on complexes;
create policy complexes_select_etablissement on complexes
  for select using (my_role() = 'etablissement' and id = (select complexe_id from etablissements where id = my_etablissement_id()));
drop policy if exists complexes_select_surveillant on complexes;
create policy complexes_select_surveillant on complexes
  for select using (
    my_role() = 'surveillant'
    and (my_etablissement_id() is null or id = (select complexe_id from etablissements where id = my_etablissement_id()))
  );

-- exam_schedules
drop policy if exists exam_schedules_select_etablissement on exam_schedules;
create policy exam_schedules_select_etablissement on exam_schedules
  for select using (scoped_to_etablissement(etablissement_id));

-- candidates
drop policy if exists candidates_select_etablissement on candidates;
create policy candidates_select_etablissement on candidates
  for select using (scoped_to_etablissement(etablissement_id));

-- exam_sessions
drop policy if exists exam_sessions_select_etablissement on exam_sessions;
create policy exam_sessions_select_etablissement on exam_sessions
  for select using (
    exists (select 1 from exam_schedules sch where sch.id = exam_sessions.exam_schedule_id and scoped_to_etablissement(sch.etablissement_id))
  );
drop policy if exists exam_sessions_insert_surveillant on exam_sessions;
create policy exam_sessions_insert_surveillant on exam_sessions
  for insert with check (
    my_role() = 'surveillant'
    and exists (select 1 from exam_schedules sch where sch.id = exam_sessions.exam_schedule_id and scoped_to_etablissement(sch.etablissement_id))
  );
drop policy if exists exam_sessions_update_surveillant on exam_sessions;
create policy exam_sessions_update_surveillant on exam_sessions
  for update using (
    my_role() = 'surveillant'
    and exists (select 1 from exam_schedules sch where sch.id = exam_sessions.exam_schedule_id and scoped_to_etablissement(sch.etablissement_id))
  );

-- incident_reports
drop policy if exists incident_reports_select_etablissement on incident_reports;
create policy incident_reports_select_etablissement on incident_reports
  for select using (
    exists (select 1 from exam_schedules sch where sch.id = incident_reports.exam_schedule_id and scoped_to_etablissement(sch.etablissement_id))
  );
drop policy if exists incident_reports_insert_surveillant on incident_reports;
create policy incident_reports_insert_surveillant on incident_reports
  for insert with check (
    my_role() = 'surveillant' and reported_by = auth.uid()
    and exists (select 1 from exam_schedules sch where sch.id = incident_reports.exam_schedule_id and scoped_to_etablissement(sch.etablissement_id))
  );

-- audit_logs
drop policy if exists audit_logs_select_etablissement on audit_logs;
create policy audit_logs_select_etablissement on audit_logs
  for select using (scoped_to_etablissement(etablissement_id));
