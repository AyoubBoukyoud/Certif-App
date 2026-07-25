// Certif-App online platform — account management Edge Function.
//
// Single entry point (service-role key, never exposed to the frontend) for
// every privileged account operation the dashboard needs:
//   - create  : regional -> complexe, complexe -> etablissement,
//               etablissement -> surveillant (auth user + entity row +
//               profile, in the direction the org chart allows) — PLUS
//               national -> regional/complexe/etablissement/surveillant,
//               anywhere in the tree (national has no region/complexe/
//               etablissement of its own, so the target parent id — or a
//               brand new region name — must be passed explicitly in the
//               request body; see handleCreate below).
//   - update / toggle_active / reset_password : same hierarchy, acting on
//               an existing profile the caller is allowed to manage.
//               national may manage any non-national profile.
//   - delete  : same hierarchy/permission check, but deleting a complexe or
//               etablissement CASCADES — every établissement/candidat/
//               surveillant/session/import under it goes too (see
//               0006_cascade_deletes.sql). Deleting a regional/surveillant
//               profile only ever removes that one login.
//
// Deploy: supabase functions deploy manage-user
// (needs SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY set as
// function secrets — see `supabase secrets set` / the project dashboard).
import { createClient, type SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

type Role = "national" | "regional" | "complexe" | "etablissement" | "surveillant";

interface CallerProfile {
  id: string;
  role: Role;
  region_id: string | null;
  complexe_id: string | null;
  etablissement_id: string | null;
  is_active: boolean;
}

// Who may create an account of which role, and which single step down the
// chain it must be.
const CREATE_PERMISSIONS: Record<Role, Role | undefined> = {
  national: undefined,
  regional: "complexe",
  complexe: "etablissement",
  etablissement: "surveillant",
  surveillant: undefined,
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS_HEADERS });
  if (req.method !== "POST") return json({ error: "Méthode non autorisée." }, 405);

  const authHeader = req.headers.get("Authorization");
  if (!authHeader) return json({ error: "Non authentifié." }, 401);

  const url = Deno.env.get("SUPABASE_URL")!;
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  // Scoped to the caller's own JWT — used only to establish who is calling
  // (via the profiles_select_self RLS policy), never for the writes below.
  const callerClient = createClient(url, anonKey, {
    global: { headers: { Authorization: authHeader } },
  });
  const {
    data: { user: callerUser },
  } = await callerClient.auth.getUser();
  if (!callerUser) return json({ error: "Session invalide." }, 401);

  const { data: caller, error: callerError } = await callerClient
    .from("profiles")
    .select("id, role, region_id, complexe_id, etablissement_id, is_active")
    .eq("id", callerUser.id)
    .single();
  if (callerError || !caller) return json({ error: "Profil introuvable." }, 403);
  // profiles_select_self (unlike my_role()) doesn't gate on is_active, and
  // this function writes through the service-role client — bypassing RLS
  // entirely — so a deactivated account's still-valid JWT must be rejected
  // explicitly here, or deactivation would only ever block the dashboard UI.
  if (!caller.is_active) return json({ error: "Compte désactivé." }, 403);

  const admin = createClient(url, serviceKey);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Corps de requête invalide." }, 400);
  }

  const action = body.action as string;
  try {
    if (action === "create") return await handleCreate(admin, caller as CallerProfile, body);
    if (action === "update") return await handleUpdate(admin, caller as CallerProfile, body);
    if (action === "toggle_active") return await handleToggleActive(admin, caller as CallerProfile, body);
    if (action === "reset_password") return await handleResetPassword(admin, caller as CallerProfile, body);
    if (action === "delete") return await handleDelete(admin, caller as CallerProfile, body);
    return json({ error: `Action inconnue : ${action}` }, 400);
  } catch (err) {
    return json({ error: err instanceof Error ? err.message : "Erreur interne." }, 500);
  }
});

async function handleCreate(admin: SupabaseClient, caller: CallerProfile, body: Record<string, unknown>) {
  const role = body.role as Role;
  const email = String(body.email ?? "").trim();
  const password = String(body.password ?? "");
  const fullName = String(body.full_name ?? "").trim();
  const entityName = body.entity_name ? String(body.entity_name).trim() : undefined;

  if (!email || !password || !fullName) return json({ error: "Champs requis manquants." }, 400);
  if (password.length < 8) return json({ error: "Mot de passe trop court (8 caractères minimum)." }, 400);

  // national is a super-caller: it may create any of the four roles below
  // it, anywhere in the tree — every other role is still limited to the one
  // child role CREATE_PERMISSIONS grants it, from its own subtree.
  const isNational = caller.role === "national";
  if (isNational) {
    if (!["regional", "complexe", "etablissement", "surveillant"].includes(role)) {
      return json({ error: "Rôle non gérable depuis ce compte." }, 400);
    }
  } else if (CREATE_PERMISSIONS[caller.role] !== role) {
    return json({ error: "Vous n'êtes pas autorisé à créer ce type de compte." }, 403);
  }

  const { data: created, error: createError } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });
  if (createError || !created.user) {
    return json({ error: createError?.message ?? "Échec de la création du compte." }, 400);
  }
  const userId = created.user.id;

  // Roll back the auth user (and, if it was already created, the entity row)
  // if anything below fails, so a partial failure never leaves an orphaned
  // login or an orphaned region/complexe/etablissement with no owning account.
  async function rollback(
    message: string,
    cleanup?: { table: "regions" | "complexes" | "etablissements"; id: string }
  ) {
    if (cleanup) await admin.from(cleanup.table).delete().eq("id", cleanup.id);
    await admin.auth.admin.deleteUser(userId);
    return json({ error: message }, 400);
  }

  if (role === "regional") {
    // Only national creates regional accounts — there is no role above
    // regional in CREATE_PERMISSIONS, so this branch is national-only.
    let regionId = body.region_id ? String(body.region_id) : undefined;
    const newRegionName = body.new_region_name ? String(body.new_region_name).trim() : undefined;
    if (!regionId && newRegionName) {
      const { data: region, error } = await admin
        .from("regions")
        .insert({ name: newRegionName })
        .select()
        .single();
      if (error || !region) return rollback(error?.message ?? "Échec de création de la région.");
      regionId = region.id;
    }
    if (!regionId) return rollback("Région requise (existante ou nouvelle).");

    const { error: profileError } = await admin.from("profiles").insert({
      id: userId,
      role: "regional",
      region_id: regionId,
      full_name: fullName,
      login: email,
    });
    if (profileError) {
      return rollback(profileError.message, newRegionName ? { table: "regions", id: regionId } : undefined);
    }
    return json({ user_id: userId, region_id: regionId });
  }

  if (role === "complexe") {
    // Regional creates under its own region; national must say which region.
    const regionId = isNational
      ? body.region_id
        ? String(body.region_id)
        : undefined
      : caller.region_id ?? undefined;
    if (!regionId) {
      return rollback(isNational ? "Région requise." : "Votre compte n'est rattaché à aucune région.");
    }
    if (!entityName) return rollback("Nom du complexe requis.");
    const { data: complexe, error } = await admin
      .from("complexes")
      .insert({ region_id: regionId, name: entityName, created_by: caller.id })
      .select()
      .single();
    if (error || !complexe) return rollback(error?.message ?? "Échec de création du complexe.");

    const { error: profileError } = await admin.from("profiles").insert({
      id: userId,
      role: "complexe",
      complexe_id: complexe.id,
      full_name: fullName,
      login: email,
    });
    if (profileError) return rollback(profileError.message, { table: "complexes", id: complexe.id });
    return json({ user_id: userId, entity: complexe });
  }

  if (role === "etablissement") {
    // Complexe creates under its own complexe; national must say which one.
    const complexeId = isNational
      ? body.complexe_id
        ? String(body.complexe_id)
        : undefined
      : caller.complexe_id ?? undefined;
    if (!complexeId) {
      return rollback(isNational ? "Complexe requis." : "Votre compte n'est rattaché à aucun complexe.");
    }
    if (!entityName) return rollback("Nom de l'établissement requis.");
    const { data: complexeRow, error: complexeError } = await admin
      .from("complexes")
      .select("region_id")
      .eq("id", complexeId)
      .single();
    if (complexeError || !complexeRow) return rollback("Complexe introuvable.");

    const { data: etab, error } = await admin
      .from("etablissements")
      .insert({
        region_id: complexeRow.region_id,
        complexe_id: complexeId,
        name: entityName,
        login: email,
        created_by: caller.id,
      })
      .select()
      .single();
    if (error || !etab) return rollback(error?.message ?? "Échec de création de l'établissement.");

    const { error: profileError } = await admin.from("profiles").insert({
      id: userId,
      role: "etablissement",
      etablissement_id: etab.id,
      full_name: fullName,
      login: email,
    });
    if (profileError) return rollback(profileError.message, { table: "etablissements", id: etab.id });
    return json({ user_id: userId, entity: etab });
  }

  if (role === "surveillant") {
    // Etablissement creates under itself; national must say which one, or
    // pass all_etablissements to create a "roaming" surveillant (null
    // etablissement_id — see 0005_surveillant_all_etablissements.sql, where
    // that null is read as "every établissement" instead of none).
    const roaming = isNational && body.all_etablissements === true;
    const etablissementId = roaming
      ? null
      : isNational
        ? body.etablissement_id
          ? String(body.etablissement_id)
          : undefined
        : caller.etablissement_id ?? undefined;
    if (!roaming && !etablissementId) {
      return rollback(isNational ? "Établissement requis." : "Votre compte n'est rattaché à aucun établissement.");
    }
    const { error: profileError } = await admin.from("profiles").insert({
      id: userId,
      role: "surveillant",
      etablissement_id: etablissementId,
      full_name: fullName,
      login: email,
    });
    if (profileError) return rollback(profileError.message);
    return json({ user_id: userId });
  }

  return rollback("Rôle inconnu.");
}

/** Fetches the target profile and checks it falls within the caller's
 * subtree (regional > complexe > etablissement > surveillant). */
async function loadManageableTarget(admin: SupabaseClient, caller: CallerProfile, profileId: string) {
  const { data: target, error } = await admin
    .from("profiles")
    .select("id, role, complexe_id, etablissement_id")
    .eq("id", profileId)
    .single();
  if (error || !target) return { target: null, allowed: false as const };

  // national manages anyone except another national account — that guard
  // stays out of the RLS layer (this function runs on the service-role
  // client, bypassing RLS) so a compromised/careless national session can't
  // deactivate or delete the only other super-admin accounts.
  if (caller.role === "national") {
    return { target, allowed: target.role !== "national" };
  }
  if (caller.role === "regional" && target.role === "complexe") {
    const { data: c } = await admin.from("complexes").select("region_id").eq("id", target.complexe_id).single();
    return { target, allowed: c?.region_id === caller.region_id };
  }
  if (caller.role === "complexe" && target.role === "etablissement") {
    const { data: e } = await admin
      .from("etablissements")
      .select("complexe_id")
      .eq("id", target.etablissement_id)
      .single();
    return { target, allowed: e?.complexe_id === caller.complexe_id };
  }
  if (caller.role === "etablissement" && target.role === "surveillant") {
    return { target, allowed: target.etablissement_id === caller.etablissement_id };
  }
  return { target, allowed: false as const };
}

/** Edits full_name / login email / the underlying entity's name (complexe or
 * etablissement — regional and surveillant have no separately-named entity
 * to rename, only the profile itself). Same "who may touch whom" check as
 * toggle/reset/delete. */
async function handleUpdate(admin: SupabaseClient, caller: CallerProfile, body: Record<string, unknown>) {
  const profileId = String(body.profile_id ?? "");
  const fullName = body.full_name ? String(body.full_name).trim() : undefined;
  const entityName = body.entity_name ? String(body.entity_name).trim() : undefined;
  const email = body.email ? String(body.email).trim() : undefined;
  if (!fullName && !email && !entityName) return json({ error: "Rien à modifier." }, 400);

  const { target, allowed } = await loadManageableTarget(admin, caller, profileId);
  if (!allowed || !target) return json({ error: "Non autorisé sur ce compte." }, 403);

  if (email) {
    const { error } = await admin.auth.admin.updateUserById(profileId, { email });
    if (error) return json({ error: error.message }, 400);
  }

  const profileUpdate: Record<string, unknown> = {};
  if (fullName) profileUpdate.full_name = fullName;
  if (email) profileUpdate.login = email;
  if (Object.keys(profileUpdate).length > 0) {
    const { error } = await admin.from("profiles").update(profileUpdate).eq("id", profileId);
    if (error) return json({ error: error.message }, 400);
  }

  if (target.role === "complexe" && target.complexe_id) {
    const entityUpdate: Record<string, unknown> = {};
    if (entityName) entityUpdate.name = entityName;
    if (Object.keys(entityUpdate).length > 0) {
      const { error } = await admin.from("complexes").update(entityUpdate).eq("id", target.complexe_id);
      if (error) return json({ error: error.message }, 400);
    }
  } else if (target.role === "etablissement" && target.etablissement_id) {
    const entityUpdate: Record<string, unknown> = {};
    if (entityName) entityUpdate.name = entityName;
    if (email) entityUpdate.login = email;
    if (Object.keys(entityUpdate).length > 0) {
      const { error } = await admin.from("etablissements").update(entityUpdate).eq("id", target.etablissement_id);
      if (error) return json({ error: error.message }, 400);
    }
  }

  return json({ ok: true });
}

async function handleToggleActive(admin: SupabaseClient, caller: CallerProfile, body: Record<string, unknown>) {
  const profileId = String(body.profile_id ?? "");
  const isActive = Boolean(body.is_active);
  const { allowed } = await loadManageableTarget(admin, caller, profileId);
  if (!allowed) return json({ error: "Non autorisé sur ce compte." }, 403);

  const { error } = await admin.from("profiles").update({ is_active: isActive }).eq("id", profileId);
  if (error) return json({ error: error.message }, 400);
  return json({ ok: true });
}

async function handleResetPassword(admin: SupabaseClient, caller: CallerProfile, body: Record<string, unknown>) {
  const profileId = String(body.profile_id ?? "");
  const newPassword = String(body.new_password ?? "");
  if (newPassword.length < 8) return json({ error: "Mot de passe trop court (8 caractères minimum)." }, 400);
  const { allowed } = await loadManageableTarget(admin, caller, profileId);
  if (!allowed) return json({ error: "Non autorisé sur ce compte." }, 403);

  const { error } = await admin.auth.admin.updateUserById(profileId, { password: newPassword });
  if (error) return json({ error: error.message }, 400);
  return json({ ok: true });
}

async function handleDelete(admin: SupabaseClient, caller: CallerProfile, body: Record<string, unknown>) {
  const profileId = String(body.profile_id ?? "");
  const { target, allowed } = await loadManageableTarget(admin, caller, profileId);
  if (!allowed || !target) return json({ error: "Non autorisé sur ce compte." }, 403);

  // complexe/etablissement own an entire subtree (see
  // 0006_cascade_deletes.sql) — deleting their entity row cascades away
  // every établissement/candidat/surveillant/session/import under it, not
  // just the one login being acted on.
  if (target.role === "complexe" && target.complexe_id) {
    return await cascadeDeleteComplexe(admin, target.complexe_id);
  }
  if (target.role === "etablissement" && target.etablissement_id) {
    return await cascadeDeleteEtablissement(admin, target.etablissement_id);
  }

  // regional / surveillant: no owned entity to cascade — just this one
  // profile + login.
  // profiles.id -> auth.users(id) has no ON DELETE CASCADE (plain FK, NO
  // ACTION) — deleting the auth user first would fail with a foreign-key
  // violation while the profile row still references it, so the profile row
  // must go first.
  const { error: profileError } = await admin.from("profiles").delete().eq("id", profileId);
  if (profileError) return json({ error: profileError.message }, 400);

  const { error } = await admin.auth.admin.deleteUser(profileId);
  if (error) return json({ error: error.message }, 400);
  return json({ ok: true });
}

/** Deletes every auth.users login gathered in `profileIds` — best-effort,
 * after the profiles rows referencing them are already gone (cascaded away
 * by the caller). A failure here leaves a login with no profile, which the
 * dashboard already treats as "profil introuvable" — better than blocking
 * the whole cascade over one flaky Auth Admin API call. */
async function deleteLogins(admin: SupabaseClient, profileIds: string[]) {
  for (const id of profileIds) {
    await admin.auth.admin.deleteUser(id);
  }
}

/** Deletes a complexe and its whole subtree (établissements, their
 * surveillant/établissement accounts, candidats, sessions, imports) in one
 * shot. 0006_cascade_deletes.sql makes the entity/profile rows disappear the
 * moment the `complexes` row goes — this only has to collect every affected
 * auth.users login *first* (profiles.id -> auth.users has no DB-level
 * cascade, by design) so they can be removed once nothing references them. */
async function cascadeDeleteComplexe(admin: SupabaseClient, complexeId: string) {
  const { data: etabs } = await admin.from("etablissements").select("id").eq("complexe_id", complexeId);
  const etabIds = (etabs ?? []).map((e) => e.id as string);

  const { data: complexeProfiles } = await admin.from("profiles").select("id").eq("complexe_id", complexeId);
  const profileIds = (complexeProfiles ?? []).map((p) => p.id as string);
  if (etabIds.length > 0) {
    const { data: etabProfiles } = await admin.from("profiles").select("id").in("etablissement_id", etabIds);
    profileIds.push(...(etabProfiles ?? []).map((p) => p.id as string));
  }

  const { error } = await admin.from("complexes").delete().eq("id", complexeId);
  if (error) return json({ error: error.message }, 400);

  await deleteLogins(admin, profileIds);
  return json({ ok: true, deleted_accounts: profileIds.length });
}

/** Deletes an établissement and its whole subtree (surveillant accounts,
 * candidats, sessions, imports) — same reasoning as cascadeDeleteComplexe. */
async function cascadeDeleteEtablissement(admin: SupabaseClient, etablissementId: string) {
  const { data: profiles } = await admin.from("profiles").select("id").eq("etablissement_id", etablissementId);
  const profileIds = (profiles ?? []).map((p) => p.id as string);

  const { error } = await admin.from("etablissements").delete().eq("id", etablissementId);
  if (error) return json({ error: error.message }, 400);

  await deleteLogins(admin, profileIds);
  return json({ ok: true, deleted_accounts: profileIds.length });
}
