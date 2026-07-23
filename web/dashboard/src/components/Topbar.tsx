import { useAuth } from "../lib/AuthContext";
import { NotificationsBell } from "./NotificationsBell";
import { ThemeToggle } from "./ThemeToggle";

const ROLE_LABELS: Record<string, string> = {
  national: "Direction Nationale",
  regional: "Direction Régionale",
  complexe: "Complexe de Formation",
  etablissement: "Administration d'établissement",
  surveillant: "Surveillant",
};

export function Topbar() {
  const { profile, signOut } = useAuth();

  return (
    <header className="topbar">
      <input
        className="topbar-search"
        type="search"
        placeholder="Recherche (bientôt disponible)"
        disabled
      />
      <div className="topbar-right">
        <ThemeToggle />
        <NotificationsBell />
        <div className="topbar-user">
          <div className="topbar-user-info">
            <strong>{profile?.full_name}</strong>
            <span>{profile ? ROLE_LABELS[profile.role] : ""}</span>
          </div>
          <button onClick={() => signOut()}>Déconnexion</button>
        </div>
      </div>
    </header>
  );
}
