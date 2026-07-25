// Module-scope cache (not React state) — survives a dashboard page
// unmounting when the user clicks to another sidebar link and back, since
// the JS module itself stays loaded for the whole tab session. Used to prime
// a page's fetched-data state synchronously (via useLayoutEffect, before the
// browser paints) instead of starting from an empty array and waiting on the
// network — that gap is what produced the visible "reset then repopulate"
// flicker. Wiped only on a real page reload; refresh() calls still keep the
// data live by writing through on every successful fetch.
const cache = new Map<string, unknown>();

export function readCache<T>(key: string): T | undefined {
  return cache.get(key) as T | undefined;
}

export function writeCache<T>(key: string, value: T): void {
  cache.set(key, value);
}
