import { FunctionsHttpError } from "@supabase/supabase-js";
import { supabase } from "./supabaseClient";

export type ManagedRole = "regional" | "complexe" | "etablissement" | "surveillant";

interface ManageUserOk {
  error?: undefined;
  [key: string]: unknown;
}
interface ManageUserErr {
  error: string;
}

async function invoke(body: Record<string, unknown>): Promise<{ error: string | null }> {
  const { data, error } = await supabase.functions.invoke<ManageUserOk | ManageUserErr>(
    "manage-user",
    { body }
  );
  if (error) {
    // supabase-js's FunctionsHttpError.message is always the generic "Edge
    // Function returned a non-2xx status code" — the actual reason the
    // function sent back (e.g. "Rôle non gérable depuis ce compte.") is in
    // the raw Response on `.context` and has to be read out separately.
    if (error instanceof FunctionsHttpError) {
      try {
        const body = (await error.context.json()) as { error?: string };
        if (body?.error) return { error: body.error };
      } catch {
        // context wasn't JSON (network/relay failure) — fall through
      }
    }
    return { error: error.message };
  }
  if (data && "error" in data && data.error) return { error: data.error };
  return { error: null };
}

/** Creates a Régionale/Complexe/Établissement/Surveillant account: auth user
 * + entity row (regional -> region, complexe/etablissement — surveillant has
 * none, it's profiles-only) + profile. Server-side only (service role) —
 * see supabase/functions/manage-user/index.ts.
 *
 * `regionId`/`complexeId`/`etablissementId` are only required when the
 * caller is a 'national' super-admin creating an account outside its own
 * subtree (it has none of its own) — a regional/complexe/etablissement
 * caller creating its one allowed child role has these inferred server-side
 * from its own profile and can omit them. */
export function createAccount(params: {
  role: ManagedRole;
  email: string;
  password: string;
  fullName: string;
  entityName?: string; // required for role='complexe' | 'etablissement'
  regionId?: string; // national creating 'regional' (existing) or 'complexe'
  newRegionName?: string; // national creating 'regional' under a brand new region
  complexeId?: string; // national creating 'etablissement'
  etablissementId?: string; // national creating 'surveillant'
  allEtablissements?: boolean; // national creating a roaming 'surveillant' (all établissements)
}) {
  return invoke({
    action: "create",
    role: params.role,
    email: params.email,
    password: params.password,
    full_name: params.fullName,
    entity_name: params.entityName,
    region_id: params.regionId,
    new_region_name: params.newRegionName,
    complexe_id: params.complexeId,
    etablissement_id: params.etablissementId,
    all_etablissements: params.allEtablissements,
  });
}

/** Edits full_name / login email / the underlying entity's name (complexe or
 * etablissement — regional and surveillant have no separately-named entity).
 * Omit `entityName` for roles with no entity to rename. */
export function updateAccount(
  profileId: string,
  params: { fullName: string; email: string; entityName?: string }
) {
  return invoke({
    action: "update",
    profile_id: profileId,
    full_name: params.fullName,
    email: params.email,
    entity_name: params.entityName,
  });
}

export function toggleActive(profileId: string, isActive: boolean) {
  return invoke({ action: "toggle_active", profile_id: profileId, is_active: isActive });
}

export function resetPassword(profileId: string, newPassword: string) {
  return invoke({ action: "reset_password", profile_id: profileId, new_password: newPassword });
}

export function deleteAccount(profileId: string) {
  return invoke({ action: "delete", profile_id: profileId });
}
