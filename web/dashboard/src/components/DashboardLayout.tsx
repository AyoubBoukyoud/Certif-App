import { Outlet } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { Breadcrumb } from "./Breadcrumb";

export function DashboardLayout() {
  const { profile, loading } = useAuth();
  if (loading) return <div className="page-loading">Chargement…</div>;

  // Don't bail out to a silent blank page when there's no profile (missing
  // row, RLS denial, ...) — render the shell anyway (minus the role-specific
  // sidebar, which needs profile.role) so the Outlet's own guard
  // (ProtectedRoute) can actually show its "Profil introuvable" message.
  return (
    <div className="portal-shell">
      {profile && <Sidebar role={profile.role} />}
      <div className="portal-body">
        <Topbar />
        <div className="portal-content">
          <Breadcrumb />
          <Outlet />
        </div>
      </div>
    </div>
  );
}
