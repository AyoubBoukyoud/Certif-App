import { useEffect, useState, type FormEvent } from "react";
import { supabase } from "../lib/supabaseClient";
import type { Database } from "../lib/database.types";
import { StatTile } from "../components/charts/StatTile";
import { BarChart } from "../components/charts/BarChart";
import { Meter } from "../components/charts/Meter";
import { ActivityList } from "../components/charts/ActivityList";
import { ActiveStatusBadge } from "../components/StatusBadge";
import { Modal } from "../components/Modal";
import { AccountRowActions } from "../components/AccountRowActions";
import { AccountDetailModal } from "../components/AccountDetailModal";
import { AccountEditModal } from "../components/AccountEditModal";
import { IconPlus } from "../components/icons";
import { createAccount, toggleActive, resetPassword, updateAccount, deleteAccount } from "../lib/manageUser";

type Region = Database["public"]["Tables"]["regions"]["Row"];
type Etablissement = Database["public"]["Tables"]["etablissements"]["Row"];
type Profile = Database["public"]["Tables"]["profiles"]["Row"];

interface ExamScheduleWithRegion {
  id: string;
  exam_date: string;
  etablissements: { name: string; regions: { name: string } | null } | null;
}

interface NationalCounts {
  regions_count: number;
  etablissements_count: number;
  surveillants_count: number;
  candidats_count: number;
  examens_count: number;
}

const MONTH_FORMATTER = new Intl.DateTimeFormat("fr-FR", { month: "short", year: "numeric" });

export function NationalDashboard() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [etablissements, setEtablissements] = useState<Etablissement[]>([]);
  const [directors, setDirectors] = useState<Profile[]>([]);
  const [stats, setStats] = useState<NationalCounts | null>(null);
  const [examsByRegion, setExamsByRegion] = useState<{ label: string; value: number }[]>([]);
  const [examsByMonth, setExamsByMonth] = useState<{ label: string; value: number }[]>([]);
  const [passRate, setPassRate] = useState<{ pct: number | null; detail: string }>({
    pct: null,
    detail: "",
  });
  const [activity, setActivity] = useState<
    { id: number; event: string; created_at: string }[]
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [showNewRegional, setShowNewRegional] = useState(false);
  const [newRegionalName, setNewRegionalName] = useState("");
  const [newRegionalEmail, setNewRegionalEmail] = useState("");
  const [newRegionalPassword, setNewRegionalPassword] = useState("");
  const [newRegionalRegionId, setNewRegionalRegionId] = useState("");
  const [newRegionName, setNewRegionName] = useState("");

  const [viewingDirector, setViewingDirector] = useState<Profile | null>(null);
  const [editingDirector, setEditingDirector] = useState<Profile | null>(null);

  async function refresh() {
      // Counted individually rather than via a `national_stats` view — that
      // view was drafted but never created on the live project (see
      // database.types.ts's header note).
      const [
        r, e, p, schedulesCountRes, surveillantsCountRes, candidatesCountRes,
        sessionsRes, sessionsCountRes, attemptsRes, auditRes,
      ] = await Promise.all([
        supabase.from("regions").select("*").order("name"),
        supabase.from("etablissements").select("*"),
        supabase.from("profiles").select("*").eq("role", "regional"),
        supabase.from("exam_schedules").select("*", { count: "exact", head: true }),
        supabase.from("profiles").select("*", { count: "exact", head: true }).eq("role", "surveillant"),
        supabase.from("candidates").select("*", { count: "exact", head: true }),
        supabase
          .from("exam_schedules")
          .select("id, exam_date, etablissements(name, regions(name))"),
        supabase.from("exam_schedules").select("*", { count: "exact", head: true }),
        supabase.from("exam_sessions").select("passed"),
        supabase
          .from("audit_logs")
          .select("id, event, created_at")
          .order("created_at", { ascending: false })
          .limit(10),
      ]);

      const firstError =
        r.error ?? e.error ?? p.error ?? schedulesCountRes.error ??
        surveillantsCountRes.error ?? candidatesCountRes.error ?? sessionsRes.error ??
        sessionsCountRes.error ?? attemptsRes.error ?? auditRes.error;
      if (firstError) {
        setError(firstError.message);
        return;
      }

      setRegions(r.data ?? []);
      setEtablissements(e.data ?? []);
      setDirectors(p.data ?? []);
      setStats({
        regions_count: r.data?.length ?? 0,
        etablissements_count: e.data?.length ?? 0,
        surveillants_count: surveillantsCountRes.count ?? 0,
        candidats_count: candidatesCountRes.count ?? 0,
        examens_count: sessionsCountRes.count ?? 0,
      });

      const sessions = (sessionsRes.data ?? []) as unknown as ExamScheduleWithRegion[];

      const byRegion = new Map<string, number>();
      const byMonth = new Map<string, number>();
      for (const s of sessions) {
        const regionName = s.etablissements?.regions?.name ?? "Sans région";
        byRegion.set(regionName, (byRegion.get(regionName) ?? 0) + 1);
        const monthLabel = MONTH_FORMATTER.format(new Date(s.exam_date));
        byMonth.set(monthLabel, (byMonth.get(monthLabel) ?? 0) + 1);
      }
      setExamsByRegion(
        Array.from(byRegion.entries()).map(([label, value]) => ({ label, value }))
      );
      setExamsByMonth(
        Array.from(byMonth.entries()).map(([label, value]) => ({ label, value }))
      );

      const graded = (attemptsRes.data ?? []).filter((a) => a.passed !== null);
      const passedCount = graded.filter((a) => a.passed).length;
      setPassRate({
        pct: graded.length > 0 ? (passedCount / graded.length) * 100 : null,
        detail: `${passedCount}/${graded.length} candidats admis`,
      });

      setActivity(auditRes.data ?? []);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onCreateRegional(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const { error } = await createAccount({
      role: "regional",
      email: newRegionalEmail,
      password: newRegionalPassword,
      fullName: newRegionalName,
      regionId: newRegionalRegionId || undefined,
      newRegionName: newRegionalRegionId ? undefined : newRegionName || undefined,
    });
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setShowNewRegional(false);
    setNewRegionalName("");
    setNewRegionalEmail("");
    setNewRegionalPassword("");
    setNewRegionalRegionId("");
    setNewRegionName("");
    refresh();
  }

  async function onToggleRegional(p: Profile) {
    setBusy(true);
    const { error } = await toggleActive(p.id, !p.is_active);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  async function onResetRegionalPassword(p: Profile) {
    const pwd = window.prompt(`Nouveau mot de passe temporaire pour ${p.full_name} :`);
    if (!pwd) return;
    setBusy(true);
    const { error } = await resetPassword(p.id, pwd);
    setBusy(false);
    if (error) setError(error);
  }

  async function onEditRegionalSubmit(values: { fullName: string; email: string }) {
    if (!editingDirector) return;
    setBusy(true);
    const { error } = await updateAccount(editingDirector.id, values);
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setEditingDirector(null);
    refresh();
  }

  async function onDeleteRegional(p: Profile) {
    if (!window.confirm(`Supprimer définitivement le compte de ${p.full_name} ?`)) return;
    setBusy(true);
    const { error } = await deleteAccount(p.id);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  const countByRegion = (regionId: string) =>
    etablissements.filter((et) => et.region_id === regionId).length;

  return (
    <div>
      <h1>Vue nationale</h1>
      {error && <p className="error-banner">{error}</p>}

      <div className="stat-row">
        <StatTile label="Régions" value={stats?.regions_count ?? "—"} />
        <StatTile label="Établissements" value={stats?.etablissements_count ?? "—"} />
        <StatTile label="Surveillants" value={stats?.surveillants_count ?? "—"} />
        <StatTile label="Candidats" value={stats?.candidats_count ?? "—"} />
        <StatTile label="Examens" value={stats?.examens_count ?? "—"} />
      </div>

      <div className="chart-grid">
        <section className="card">
          <h2>Examens par région</h2>
          <BarChart data={examsByRegion} emptyMessage="Aucune session d'examen planifiée." />
        </section>
        <section className="card">
          <h2>Examens par mois</h2>
          <BarChart data={examsByMonth} emptyMessage="Aucune session d'examen planifiée." />
        </section>
        <section className="card">
          <h2>Réussite</h2>
          <Meter
            label="Taux de réussite"
            pct={passRate.pct}
            detail={passRate.detail}
            status="good"
            emptyMessage="Aucun résultat remonté pour l'instant."
          />
        </section>
      </div>

      <section className="card">
        <h2>Dernières activités</h2>
        <ActivityList items={activity} />
      </section>

      <section className="card">
        <h2>Régions</h2>
        <table>
          <thead>
            <tr>
              <th>Région</th>
              <th>Établissements</th>
              <th>Direction régionale</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {regions.map((r) => {
              const director = directors.find((d) => d.region_id === r.id);
              return (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{countByRegion(r.id)}</td>
                  <td>{director?.full_name ?? "—"}</td>
                  <td>{director ? <ActiveStatusBadge isActive={director.is_active} /> : "—"}</td>
                  <td>
                    {director && (
                      <AccountRowActions
                        isActive={director.is_active}
                        busy={busy}
                        onView={() => setViewingDirector(director)}
                        onEdit={() => setEditingDirector(director)}
                        onToggle={() => onToggleRegional(director)}
                        onResetPassword={() => onResetRegionalPassword(director)}
                        onDelete={() => onDeleteRegional(director)}
                      />
                    )}
                  </td>
                </tr>
              );
            })}
            {regions.length === 0 && (
              <tr>
                <td colSpan={5}>Aucune région enregistrée.</td>
              </tr>
            )}
          </tbody>
        </table>
        <button className="btn-icon-label" onClick={() => setShowNewRegional(true)}>
          <IconPlus size={14} /> Nouvelle direction régionale
        </button>
      </section>

      {viewingDirector && (
        <AccountDetailModal
          title={viewingDirector.full_name}
          onClose={() => setViewingDirector(null)}
          fields={[
            ["Nom complet", viewingDirector.full_name],
            ["Email (login)", viewingDirector.login],
            ["Rôle", "Direction régionale"],
            ["Région", regions.find((r) => r.id === viewingDirector.region_id)?.name],
            ["Établissements", countByRegion(viewingDirector.region_id ?? "")],
            ["Statut", viewingDirector.is_active ? "Actif" : "Désactivé"],
            ["Créé le", new Date(viewingDirector.created_at).toLocaleString("fr-FR")],
          ]}
        />
      )}

      {editingDirector && (
        <AccountEditModal
          title={`Modifier — ${editingDirector.full_name}`}
          initialFullName={editingDirector.full_name}
          initialEmail={editingDirector.login ?? ""}
          busy={busy}
          onSubmit={onEditRegionalSubmit}
          onClose={() => setEditingDirector(null)}
        />
      )}

      {showNewRegional && (
        <Modal title="Nouvelle direction régionale" onClose={() => setShowNewRegional(false)}>
          <form className="inline-form" onSubmit={onCreateRegional} style={{ flexDirection: "column" }}>
            <input
              placeholder="Nom du directeur régional"
              value={newRegionalName}
              onChange={(e) => setNewRegionalName(e.target.value)}
              required
            />
            <select
              value={newRegionalRegionId}
              onChange={(e) => setNewRegionalRegionId(e.target.value)}
            >
              <option value="">— Nouvelle région —</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
            {!newRegionalRegionId && (
              <input
                placeholder="Nom de la nouvelle région"
                value={newRegionName}
                onChange={(e) => setNewRegionName(e.target.value)}
                required
              />
            )}
            <input
              type="email"
              placeholder="Email (login du compte DR)"
              value={newRegionalEmail}
              onChange={(e) => setNewRegionalEmail(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Mot de passe temporaire"
              value={newRegionalPassword}
              onChange={(e) => setNewRegionalPassword(e.target.value)}
              minLength={8}
              required
            />
            <button type="submit" disabled={busy}>
              {busy ? "Création…" : "Créer"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
