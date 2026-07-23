-- Certif-App — seed d'un compte super-admin ('national'), sans région /
-- complexe / établissement propre : avec la migration
-- 0002_national_full_access.sql appliquée, ce compte peut tout lire et tout
-- écrire (créer/gérer des régions, complexes, établissements, surveillants,
-- sessions d'examen, candidats…) depuis le dashboard.
--
-- ⚠️ Mot de passe volontairement identique au login ('admin@admin.com'), tel
-- que demandé — c'est un mot de passe trivialement devinable pour un compte
-- à tous les droits. À changer dès que possible (dashboard national -> pas
-- encore d'auto-changement de mot de passe ; sinon via
-- supabase.auth.admin.updateUserById ou le SQL Editor).
--
-- Run once. Si un compte 'admin@admin.com' existe déjà, ce script échouera
-- sur la contrainte unique — c'est voulu (pas de doublon silencieux).

do $$
declare
  v_user_id uuid := gen_random_uuid();
  v_email text := 'admin@admin.com';
  v_password text := 'admin@admin.com';
begin
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

  insert into profiles (id, role, full_name, login, is_active)
  values (v_user_id, 'national', 'Super Administrateur', v_email, true);
end $$;

select role, full_name, login, 'admin@admin.com' as password
from profiles where login = 'admin@admin.com';
