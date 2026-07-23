import { useEffect } from "react";
import { supabase } from "../lib/supabaseClient";

/** Subscribes to Postgres changes on `table` and calls `onChange` for every
 * INSERT/UPDATE/DELETE — callers re-run their own fetch from there rather
 * than trying to patch state from the (partial) payload. `filter` follows
 * Supabase Realtime's `column=eq.value` syntax; omit for no filter. */
export function useRealtimeTable(table: string, onChange: () => void, filter?: string) {
  useEffect(() => {
    const channel = supabase
      .channel(`rt-${table}-${filter ?? "all"}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table, ...(filter ? { filter } : {}) },
        () => onChange()
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table, filter]);
}
