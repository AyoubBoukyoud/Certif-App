import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../lib/AuthContext";
import type { UserRole } from "../lib/database.types";

export function ProtectedRoute({
  children,
  allow,
}: {
  children: ReactNode;
  allow: UserRole[];
}) {
  const { session, profile, loading } = useAuth();

  if (loading) return <div className="page-loading">Chargement…</div>;
  if (!session) return <Navigate to="/login" replace />;
  if (!profile) {
    // A session with no matching profiles row must NOT redirect to /login —
    // Login.tsx redirects straight back to "/" whenever a session exists,
    // so bouncing here would loop the two routes forever and hang the tab.
    return (
      <div className="page-loading">
        <p className="error-banner">
          Profil introuvable pour ce compte. Contactez votre administrateur.
        </p>
      </div>
    );
  }
  if (!profile.is_active) {
    return (
      <div className="page-loading">
        <p className="error-banner">
          Compte désactivé. Contactez votre administrateur pour le réactiver.
        </p>
      </div>
    );
  }
  if (!allow.includes(profile.role)) return <Navigate to="/" replace />;

  return <>{children}</>;
}
