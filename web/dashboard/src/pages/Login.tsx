import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import ofpptLogo from "../assets/ofppt-logo.png";

export function Login() {
  const { session, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Once signIn() succeeds, AuthContext's session updates and this re-renders
  // — bounce to "/", which resolves the right dashboard by role (RoleHome in
  // App.tsx). Also covers an already-authenticated user landing on /login
  // directly (e.g. a stale bookmark).
  if (session) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const { error } = await signIn(email, password);
    setSubmitting(false);
    if (error) setError(error);
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-logo-badge">
          <img src={ofpptLogo} alt="OFPPT" />
        </div>

        <div className="auth-heading">
          <h1>Certif-App</h1>
          <p className="subtitle">Plateforme de certification MOS</p>
        </div>

        <div className="auth-field">
          <label htmlFor="email">Identifiant</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="nom@ofppt.ma"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="auth-field">
          <label htmlFor="password">Mot de passe</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <p className="error-banner">{error}</p>}

        <button type="submit" className="auth-submit" disabled={submitting}>
          {submitting ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
