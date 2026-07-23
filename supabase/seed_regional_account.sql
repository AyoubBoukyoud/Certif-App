-- Certif-App — seed d'un compte Direction Régionale (DR) de test, dans la
-- même région que seed_test_data.sql. Même pattern (insertion directe dans
-- auth.users/auth.identities) et même mot de passe que les autres comptes
-- de test : Test1234!
--
-- Run once. Si un compte 'regional.test@test.local' existe déjà, ce script
-- échouera sur la contrainte unique — c'est voulu (pas de doublon silencieux).

do $$
declare
  v_region_id uuid;
  v_user_id uuid := gen_random_uuid();
  v_email text := 'regional.test@test.local';
  v_password text := 'Test1234!';
begin
  select id into v_region_id from regions order by name limit 1;
  if v_region_id is null then
    raise exception 'Aucune région trouvée — créez-en une avant de lancer ce script.';
  end if;

  insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at, confirmation_token, email_change, email_change_token_new, recovery_token
  ) values (
    '00000000-0000-0000-0000-000000000000', v_user_id, 'authenticated', 'authenticated',
    v_email, crypt(v_password, gen_salt('bf')),
    now(), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb,
    now(), now(), '', '', '', ''
  );
  insert into auth.identities (
    id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
  ) values (
    gen_random_uuid(), v_user_id::text, v_user_id,
    jsonb_build_object('sub', v_user_id::text, 'email', v_email),
    'email', now(), now(), now()
  );

  insert into profiles (id, role, region_id, full_name, login, is_active)
  values (v_user_id, 'regional', v_region_id, 'Direction Régionale (test)', v_email, true);
end $$;

select role, full_name, login, 'Test1234!' as password
from profiles where login = 'regional.test@test.local';
