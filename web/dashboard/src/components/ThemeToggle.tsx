import { useEffect, useState } from "react";
import { applyTheme, currentEffectiveTheme, type Theme } from "../lib/theme";
import { IconSun, IconMoon } from "./icons";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(currentEffectiveTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return (
    <button
      className="theme-toggle"
      onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      aria-label="Basculer le thème clair/sombre"
      title={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
    >
      {theme === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
    </button>
  );
}
