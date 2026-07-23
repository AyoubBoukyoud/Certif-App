const STORAGE_KEY = "certifapp-theme";

export type Theme = "light" | "dark";

export function getStoredTheme(): Theme | null {
  const value = localStorage.getItem(STORAGE_KEY);
  return value === "light" || value === "dark" ? value : null;
}

export function applyTheme(theme: Theme | null): void {
  if (theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
  } else {
    delete document.documentElement.dataset.theme;
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function currentEffectiveTheme(): Theme {
  const stored = getStoredTheme();
  if (stored) return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
