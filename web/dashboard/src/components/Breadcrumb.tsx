import { useLocation } from "react-router-dom";

// useMatches()+handle would be the natural fit here, but it requires a data
// router (createBrowserRouter) — this app uses the classic <BrowserRouter>,
// under which useMatches() throws unconditionally. A plain pathname lookup
// avoids that migration for what is otherwise a one-line breadcrumb.
const LABELS: Record<string, string> = {
  "/national": "Tableau de bord",
  "/regional": "Ma région",
  "/complexe": "Mon complexe",
  "/etablissement": "Mon établissement",
  "/surveillant": "Mes sessions",
};

export function Breadcrumb() {
  const { pathname } = useLocation();
  const label = LABELS[pathname];
  if (!label) return null;

  return (
    <nav className="breadcrumb" aria-label="Fil d'ariane">
      <span className="breadcrumb-item">{label}</span>
    </nav>
  );
}
