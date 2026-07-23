-- Certif-App — seed de données de test.
-- Crée, dans la première région trouvée : 4 complexes, 4 établissements par
-- complexe (16 au total), et 40 candidats par établissement (640 au total).
-- Mot de passe unique pour TOUS les comptes créés ici : Test1234!
--
-- Insère directement dans auth.users / auth.identities (schéma interne de
-- Supabase Auth) — pratique courante pour semer des comptes de test en une
-- seule fois quand on n'a pas la CLI/l'API sous la main, mais ce n'est pas
-- un chemin officiellement garanti par Supabase. Pour de vrais comptes de
-- production, utilisez plutôt la fonction manage-user ou le Dashboard.
--
-- Prérequis : au moins une ligne dans `regions` (créée lors de l'amorçage).
-- Run once, en une seule fois, dans le SQL Editor.

do $$
declare
  v_region_id uuid;
  v_complexe_id uuid;
  v_complexe_user_id uuid;
  v_etab_id uuid;
  v_etab_user_id uuid;
  v_email text;
  v_password text := 'Test1234!';
  c int;
  e int;
  n int;
  first_names text[] := array['Ahmed','Fatima','Youssef','Khadija','Omar','Amina','Hassan','Nadia','Karim','Salma','Rachid','Leila','Mehdi','Samira','Younes','Zineb','Tarik','Imane','Bilal','Houda'];
  last_names text[] := array['El Amrani','Bennani','Alaoui','Tazi','Idrissi','Benjelloun','Chraibi','Fassi','Berrada','Squalli','Lahlou','Cherkaoui','Kettani','Sbai','Bouazza','Tahiri','Ziani','Kabbaj','Rifai','Zerouali'];
begin
  select id into v_region_id from regions order by name limit 1;
  if v_region_id is null then
    raise exception 'Aucune région trouvée — créez-en une avant de lancer ce script (voir 0001_full_schema.sql STEP 6).';
  end if;

  for c in 1..4 loop
    -- --- compte + entité Complexe ---
    v_complexe_user_id := gen_random_uuid();
    v_email := format('complexe%s@test.local', c);

    insert into auth.users (
      instance_id, id, aud, role, email, encrypted_password,
      email_confirmed_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data,
      created_at, updated_at, confirmation_token, email_change, email_change_token_new, recovery_token
    ) values (
      '00000000-0000-0000-0000-000000000000', v_complexe_user_id, 'authenticated', 'authenticated',
      v_email, crypt(v_password, gen_salt('bf')),
      now(), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb,
      now(), now(), '', '', '', ''
    );
    insert into auth.identities (
      id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
    ) values (
      gen_random_uuid(), v_complexe_user_id::text, v_complexe_user_id,
      jsonb_build_object('sub', v_complexe_user_id::text, 'email', v_email),
      'email', now(), now(), now()
    );

    insert into complexes (region_id, name)
    values (v_region_id, format('Complexe de Formation %s', c))
    returning id into v_complexe_id;

    insert into profiles (id, role, complexe_id, full_name, login, is_active)
    values (v_complexe_user_id, 'complexe', v_complexe_id, format('Responsable Complexe %s', c), v_email, true);

    for e in 1..4 loop
      -- --- compte + entité Établissement ---
      v_etab_user_id := gen_random_uuid();
      v_email := format('etab%s-%s@test.local', c, e);

      insert into auth.users (
        instance_id, id, aud, role, email, encrypted_password,
        email_confirmed_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data,
        created_at, updated_at, confirmation_token, email_change, email_change_token_new, recovery_token
      ) values (
        '00000000-0000-0000-0000-000000000000', v_etab_user_id, 'authenticated', 'authenticated',
        v_email, crypt(v_password, gen_salt('bf')),
        now(), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb,
        now(), now(), '', '', '', ''
      );
      insert into auth.identities (
        id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
      ) values (
        gen_random_uuid(), v_etab_user_id::text, v_etab_user_id,
        jsonb_build_object('sub', v_etab_user_id::text, 'email', v_email),
        'email', now(), now(), now()
      );

      insert into etablissements (region_id, complexe_id, name, login)
      values (v_region_id, v_complexe_id, format('Établissement %s.%s', c, e), v_email)
      returning id into v_etab_id;

      insert into profiles (id, role, etablissement_id, full_name, login, is_active)
      values (v_etab_user_id, 'etablissement', v_etab_id, format('Administration Établissement %s.%s', c, e), v_email, true);

      -- --- 40 candidats, sans compte (pas de login pour un candidat) ---
      for n in 1..40 loop
        insert into candidates (etablissement_id, first_name, last_name, cin, sexe)
        values (
          v_etab_id,
          first_names[1 + ((n - 1) % array_length(first_names, 1))],
          last_names[1 + ((n - 1) % array_length(last_names, 1))],
          format('SEED%s%s%s', c, e, lpad(n::text, 3, '0')),
          case when n % 2 = 0 then 'F' else 'M' end
        );
      end loop;
    end loop;
  end loop;
end $$;

-- Récapitulatif des comptes créés (à re-exécuter séparément à tout moment)
select role, full_name, login, 'Test1234!' as password
from profiles
where login like '%@test.local'
order by role desc, login;
