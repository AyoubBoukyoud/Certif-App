import { useCallback, useState, type Dispatch, type SetStateAction } from "react";

/** Like useState, but backed by sessionStorage under `key`. Dashboard pages
 * live on their own route (see App.tsx) — navigating to another sidebar
 * link unmounts them, so plain useState resets search/filters/selection
 * back to defaults every time the user comes back. sessionStorage survives
 * that remount (cleared only when the tab closes), so the view picks up
 * where the user left it. Not for fetched data itself — that still refetches
 * on mount to stay correct, this only carries the view state across. */
export function usePersistentState<T>(key: string, initialValue: T): [T, Dispatch<SetStateAction<T>>] {
  const storageKey = `certif-app:${key}`;
  const [state, setState] = useState<T>(() => {
    try {
      const stored = sessionStorage.getItem(storageKey);
      return stored !== null ? (JSON.parse(stored) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  // useCallback keeps the setter's identity stable across renders, like the
  // built-in useState setter — otherwise every consumer effect that lists it
  // as a dependency (see EtablissementDashboard's page-clamp effect) would
  // need an exhaustive-deps suppression instead.
  const setPersistentState = useCallback<Dispatch<SetStateAction<T>>>(
    (value) => {
      setState((prev) => {
        const next = typeof value === "function" ? (value as (p: T) => T)(prev) : value;
        try {
          sessionStorage.setItem(storageKey, JSON.stringify(next));
        } catch {
          // storage unavailable (private mode, quota) — state still works in-memory
        }
        return next;
      });
    },
    [storageKey]
  );

  return [state, setPersistentState];
}
