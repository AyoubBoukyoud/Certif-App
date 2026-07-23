import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import { AuthProvider, useAuth } from "./lib/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardLayout } from "./components/DashboardLayout";
import { Login } from "./pages/Login";
import { NationalDashboard } from "./pages/NationalDashboard";
import { RegionalDashboard } from "./pages/RegionalDashboard";
import { ComplexeDashboard } from "./pages/ComplexeDashboard";
import { EtablissementDashboard } from "./pages/EtablissementDashboard";
import { SurveillantDashboard } from "./pages/SurveillantDashboard";

function RoleHome() {
  const { session, profile, loading } = useAuth();
  if (loading) return <div className="page-loading">Chargement…</div>;
  // No session at all -> genuinely not logged in, /login is correct. A
  // session with no resolvable role must NOT go to /login too — Login.tsx
  // redirects straight back to "/" whenever a session exists, so the two
  // would loop forever and hang the tab instead of ever landing on either.
  if (!session) return <Navigate to="/login" replace />;
  switch (profile?.role) {
    case "national":
      return <Navigate to="/national" replace />;
    case "regional":
      return <Navigate to="/regional" replace />;
    case "complexe":
      return <Navigate to="/complexe" replace />;
    case "etablissement":
      return <Navigate to="/etablissement" replace />;
    case "surveillant":
      return <Navigate to="/surveillant" replace />;
    default:
      return (
        <div className="page-loading">
          <p className="error-banner">
            Profil introuvable pour ce compte. Contactez votre administrateur.
          </p>
        </div>
      );
  }
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<DashboardLayout />}>
            <Route
              path="/national"
              element={
                <ProtectedRoute allow={["national"]}>
                  <NationalDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/regional"
              element={
                <ProtectedRoute allow={["regional", "national"]}>
                  <RegionalDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/complexe"
              element={
                <ProtectedRoute allow={["complexe", "national"]}>
                  <ComplexeDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/etablissement"
              element={
                <ProtectedRoute allow={["etablissement", "national"]}>
                  <EtablissementDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/surveillant"
              element={
                <ProtectedRoute allow={["surveillant"]}>
                  <SurveillantDashboard />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="/" element={<RoleHome />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
