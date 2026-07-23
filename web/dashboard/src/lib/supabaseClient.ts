import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error(
    "VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY missing — check .env.local (see .env.example)."
  );
}

// Not parameterized with `Database` yet: our hand-written database.types.ts
// doesn't match supabase-js v2's newer generated-types shape (Relationships,
// __InternalSupabase, etc.) closely enough for its generic inference. Once
// the migration has run, regenerate real types (`generate_typescript_types`)
// and reinstate `createClient<Database>(...)`. Row/Insert shapes in
// database.types.ts are still used directly for annotations in the meantime.
export const supabase = createClient(url, anonKey);
