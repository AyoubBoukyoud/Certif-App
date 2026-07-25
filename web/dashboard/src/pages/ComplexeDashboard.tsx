import { useEffect, useLayoutEffect, useMemo, useState, type FormEvent } from "react";
import { useAuth } from "../lib/AuthContext";
import { supabase } from "../lib/supabaseClient";
import type { Database } from "../lib/database.types";
import { StatTile } from "../components/charts/StatTile";
import { ScheduleStatusBadge, ActiveStatusBadge } from "../components/StatusBadge";
import { Modal } from "../components/Modal";
import { AccountRowActions } from "../components/AccountRowActions";
import { AccountDetailModal } from "../components/AccountDetailModal";
import { AccountEditModal } from "../components/AccountEditModal";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal";
import { IconPlus } from "../components/icons";
import { createAccount, toggleActive, resetPassword, updateAccount, deleteAccount } from "../lib/manageUser";
import { useRealtimeTable } from "../hooks/useRealtimeTable";
import { usePersistentState } from "../lib/usePersistentState";
import { readCache, writeCache } from "../lib/dataCache";

type Etablissement = Database["public"]["Tables"]["etablissements"]["Row"];
type ExamSchedule = Database["public"]["Tables"]["exam_schedules"]["Row"];
type Profile = Database["public"]["Tables"]["profiles"]["Row"];
type IncidentReport = Database["public"]["Tables"]["incident_reports"]["Row"];
type Complexe = Database["public"]["Tables"]["complexes"]["Row"];
interface ComplexeWithRegion extends Complexe {
  regions: { name: string } | null;
}

interface CachedComplexeData {
  etablissements: Etablissement[];
  etabProfiles: Profile[];
  sessions: ExamSchedule[];
  presentCounts: Record<string, number>;
  incidents: IncidentReport[];
}

const complexeCacheKey = (complexeId: string) => `complexe-dash:data:${complexeId}`;

const todayIso = () => new Date().toISOString().slice(0, 10);

export function ComplexeDashboard() {
  const { profile } = useAuth();
  // A 'national' caller has no complexe_id of its own — it picks which
  // complexe to act as Complexe de Formation for, from every complexe that
  // exists (across all regions).
  const isNational = profile?.role === "national";
  const [allComplexes, setAllComplexes] = useState<ComplexeWithRegion[]>([]);
  const [selectedComplexeId, setSelectedComplexeId] = usePersistentState("complexe-dash:selectedComplexeId", "");
  const complexeId = isNational ? selectedComplexeId : profile?.complexe_id ?? "";

  // Lazily hydrated from the module-level cache (see lib/dataCache) so a
  // remount — e.g. clicking to another sidebar page and back — repaints the
  // last known data immediately instead of resetting to empty.
  const complexeCached = readCache<CachedComplexeData>(complexeCacheKey(complexeId));
  const [etablissements, setEtablissements] = useState<Etablissement[]>(complexeCached?.etablissements ?? []);
  const [etabProfiles, setEtabProfiles] = useState<Profile[]>(complexeCached?.etabProfiles ?? []);
  const [sessions, setSessions] = useState<ExamSchedule[]>(complexeCached?.sessions ?? []);
  const [presentCounts, setPresentCounts] = useState<Record<string, number>>(complexeCached?.presentCounts ?? {});
  const [incidents, setIncidents] = useState<IncidentReport[]>(complexeCached?.incidents ?? []);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [filterEtab, setFilterEtab] = usePersistentState("complexe-dash:filterEtab", "");
  const [filterDate, setFilterDate] = usePersistentState("complexe-dash:filterDate", "");
  const [filterStatus, setFilterStatus] = usePersistentState("complexe-dash:filterStatus", "");

  const [showNewEtab, setShowNewEtab] = useState(false);
  const [newEtabName, setNewEtabName] = useState("");
  const [newEtabEmail, setNewEtabEmail] = useState("");
  const [newEtabPassword, setNewEtabPassword] = useState("");

  const [viewingEtab, setViewingEtab] = useState<{ profile: Profile; etab: Etablissement } | null>(null);
  const [editingEtab, setEditingEtab] = useState<{ profile: Profile; etab: Etablissement } | null>(null);
  const [deletingEtab, setDeletingEtab] = useState<{ profile: Profile; etab: Etablissement } | null>(null);

  async function refresh() {
    if (!complexeId) return;
    const [et, s] = await Promise.all([
      supabase.from("etablissements").select("*").eq("complexe_id", complexeId).order("name"),
      supabase
        .from("exam_schedules")
        .select("*, etablissements!inner(complexe_id)")
        .eq("etablissements.complexe_id", complexeId)
        .order("exam_date", { ascending: false }),
    ]);
    if (et.error || s.error) {
      setError(et.error?.message ?? s.error?.message ?? "Erreur");
      return;
    }
    const etabRows = et.data ?? [];
    const scheduleRows = (s.data ?? []) as unknown as ExamSchedule[];
    setEtablissements(etabRows);
    setSessions(scheduleRows);

    const [profs, incidentsRes] = await Promise.all([
      etabRows.length > 0
        ? supabase.from("profiles").select("*").eq("role", "etablissement").in(
            "etablissement_id",
            etabRows.map((e) => e.id)
          )
        : Promise.resolve({ data: [] as Profile[], error: null }),
      scheduleRows.length > 0
        ? supabase
            .from("incident_reports")
            .select("*")
            .in("exam_schedule_id", scheduleRows.map((r) => r.id))
            .order("created_at", { ascending: false })
            .limit(10)
        : Promise.resolve({ data: [] as IncidentReport[], error: null }),
    ]);
    const nextEtabProfiles = profs.data ?? [];
    const nextIncidents = incidentsRes.data ?? [];
    setEtabProfiles(nextEtabProfiles);
    setIncidents(nextIncidents);

    const inProgressIds = scheduleRows.filter((r) => r.status === "in_progress").map((r) => r.id);
    const nextPresentCounts: Record<string, number> = {};
    if (inProgressIds.length > 0) {
      const { data: attempts } = await supabase
        .from("exam_sessions")
        .select("exam_schedule_id")
        .eq("status", "started")
        .in("exam_schedule_id", inProgressIds);
      for (const a of attempts ?? []) {
        nextPresentCounts[a.exam_schedule_id] = (nextPresentCounts[a.exam_schedule_id] ?? 0) + 1;
      }
    }
    setPresentCounts(nextPresentCounts);

    writeCache<CachedComplexeData>(complexeCacheKey(complexeId), {
      etablissements: etabRows,
      etabProfiles: nextEtabProfiles,
      sessions: scheduleRows,
      presentCounts: nextPresentCounts,
      incidents: nextIncidents,
    });
  }

  // national only: load every complexe (with its region name) for the
  // selector, defaulting to the first one once available.
  useEffect(() => {
    if (!isNational) return;
    supabase
      .from("complexes")
      .select("*, regions(name)")
      .order("name")
      .then(({ data }) => {
        const rows = (data ?? []) as unknown as ComplexeWithRegion[];
        setAllComplexes(rows);
        setSelectedComplexeId((current) => current || rows[0]?.id || "");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNational]);

  // useLayoutEffect so switching complexeId (national picking a different
  // complexe mid-session) repaints from that id's cached snapshot before the
  // browser paints, instead of flashing the previous complexe's data.
  useLayoutEffect(() => {
    if (!complexeId) return;
    const snapshot = readCache<CachedComplexeData>(complexeCacheKey(complexeId));
    setEtablissements(snapshot?.etablissements ?? []);
    setEtabProfiles(snapshot?.etabProfiles ?? []);
    setSessions(snapshot?.sessions ?? []);
    setPresentCounts(snapshot?.presentCounts ?? {});
    setIncidents(snapshot?.incidents ?? []);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [complexeId]);

  useRealtimeTable("exam_schedules", refresh);
  useRealtimeTable("exam_sessions", refresh);
  useRealtimeTable("incident_reports", refresh);

  async function onCreateEtab(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const { error } = await createAccount({
      role: "etablissement",
      email: newEtabEmail,
      password: newEtabPassword,
      fullName: newEtabName,
      entityName: newEtabName,
      complexeId: isNational ? complexeId : undefined,
    });
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setShowNewEtab(false);
    setNewEtabName("");
    setNewEtabEmail("");
    setNewEtabPassword("");
    refresh();
  }

  async function onToggleEtab(p: Profile) {
    setBusy(true);
    const { error } = await toggleActive(p.id, !p.is_active);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  async function onResetEtabPassword(p: Profile) {
    const pwd = window.prompt(`Nouveau mot de passe temporaire pour ${p.full_name} :`);
    if (!pwd) return;
    setBusy(true);
    const { error } = await resetPassword(p.id, pwd);
    setBusy(false);
    if (error) setError(error);
  }

  async function onEditEtabSubmit(values: { fullName: string; email: string; entityName?: string }) {
    if (!editingEtab) return;
    setBusy(true);
    const { error } = await updateAccount(editingEtab.profile.id, values);
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setEditingEtab(null);
    refresh();
  }

  async function onConfirmDeleteEtab() {
    if (!deletingEtab) return;
    setBusy(true);
    const { error } = await deleteAccount(deletingEtab.profile.id);
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setDeletingEtab(null);
    refresh();
  }

  const profileForEtab = (e: Etablissement) => etabProfiles.find((p) => p.etablissement_id === e.id);

  const filteredSessions = useMemo(
    () =>
      sessions.filter(
        (s) =>
          (!filterEtab || s.etablissement_id === filterEtab) &&
          (!filterDate || s.exam_date === filterDate) &&
          (!filterStatus || s.status === filterStatus)
      ),
    [sessions, filterEtab, filterDate, filterStatus]
  );

  const sessionsToday = sessions.filter((s) => s.exam_date === todayIso()).length;
  const activeEtabCount = etablissements.filter((e) => profileForEtab(e)?.is_active !== false).length;

  return (
    <div>
      <h1>Mon complexe</h1>
      {isNational && (
        <div className="toolbar" style={{ marginBottom: "1rem" }}>
          <label htmlFor="complexe-select">Complexe géré&nbsp;:</label>
          <select
            id="complexe-select"
            value={selectedComplexeId}
            onChange={(e) => setSelectedComplexeId(e.target.value)}
          >
            {allComplexes.length === 0 && <option value="">Aucun complexe</option>}
            {allComplexes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {c.regions?.name ? ` (${c.regions.name})` : ""}
              </option>
            ))}
          </select>
        </div>
      )}
      {error && <p className="error-banner">{error}</p>}

      <div className="stat-row">
        <StatTile label="Établissements actifs" value={activeEtabCount} />
        <StatTile label="Sessions aujourd'hui" value={sessionsToday} />
        <StatTile label="Incidents récents" value={incidents.length} />
      </div>

      <section className="card">
        <h2>Derniers incidents</h2>
        {incidents.length === 0 && <p className="hint">Aucun incident signalé.</p>}
        {incidents.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Description</th>
                <th>Signalé le</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((i) => (
                <tr key={i.id}>
                  <td>{i.type_incident ?? "—"}</td>
                  <td>{i.description}</td>
                  <td>{new Date(i.created_at).toLocaleString("fr-FR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Établissements</h2>
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Code</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {etablissements.map((e) => {
              const p = profileForEtab(e);
              return (
                <tr key={e.id}>
                  <td>{e.name}</td>
                  <td>{e.login ?? "—"}</td>
                  <td>{p ? <ActiveStatusBadge isActive={p.is_active} /> : "—"}</td>
                  <td>
                    {p && (
                      <AccountRowActions
                        isActive={p.is_active}
                        busy={busy}
                        onView={() => setViewingEtab({ profile: p, etab: e })}
                        onEdit={() => setEditingEtab({ profile: p, etab: e })}
                        onToggle={() => onToggleEtab(p)}
                        onResetPassword={() => onResetEtabPassword(p)}
                        onDelete={() => setDeletingEtab({ profile: p, etab: e })}
                      />
                    )}
                  </td>
                </tr>
              );
            })}
            {etablissements.length === 0 && (
              <tr>
                <td colSpan={4}>Aucun établissement.</td>
              </tr>
            )}
          </tbody>
        </table>
        <button className="btn-icon-label" onClick={() => setShowNewEtab(true)}>
          <IconPlus size={14} /> Nouvel établissement
        </button>
      </section>

      {viewingEtab && (
        <AccountDetailModal
          title={viewingEtab.etab.name}
          onClose={() => setViewingEtab(null)}
          fields={[
            ["Nom de l'établissement", viewingEtab.etab.name],
            ["Responsable", viewingEtab.profile.full_name],
            ["Email (login)", viewingEtab.profile.login],
            ["Statut", viewingEtab.profile.is_active ? "Actif" : "Désactivé"],
            ["Créé le", new Date(viewingEtab.etab.created_at).toLocaleString("fr-FR")],
          ]}
        />
      )}

      {editingEtab && (
        <AccountEditModal
          title={`Modifier — ${editingEtab.etab.name}`}
          initialFullName={editingEtab.profile.full_name}
          initialEmail={editingEtab.profile.login ?? ""}
          initialEntityName={editingEtab.etab.name}
          entityLabel="Nom de l'établissement"
          busy={busy}
          onSubmit={onEditEtabSubmit}
          onClose={() => setEditingEtab(null)}
        />
      )}

      {deletingEtab && (
        <ConfirmDeleteModal
          title={`Supprimer — ${deletingEtab.etab.name}`}
          entityName={deletingEtab.etab.name}
          warning="Tous les surveillants, candidats, sessions et imports de cet établissement seront supprimés définitivement."
          busy={busy}
          onConfirm={onConfirmDeleteEtab}
          onClose={() => setDeletingEtab(null)}
        />
      )}

      {showNewEtab && (
        <Modal title="Nouvel établissement" onClose={() => setShowNewEtab(false)}>
          <form className="inline-form" onSubmit={onCreateEtab} style={{ flexDirection: "column" }}>
            <input
              placeholder="Nom de l'établissement"
              value={newEtabName}
              onChange={(e) => setNewEtabName(e.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email (login du compte ET)"
              value={newEtabEmail}
              onChange={(e) => setNewEtabEmail(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Mot de passe temporaire"
              value={newEtabPassword}
              onChange={(e) => setNewEtabPassword(e.target.value)}
              minLength={8}
              required
            />
            <button type="submit" disabled={busy}>
              {busy ? "Création…" : "Créer"}
            </button>
          </form>
        </Modal>
      )}

      <section className="card">
        <h2>Moniteur de sessions</h2>
        <div className="toolbar">
          <select value={filterEtab} onChange={(e) => setFilterEtab(e.target.value)}>
            <option value="">Tous les établissements</option>
            {etablissements.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
          <input type="date" value={filterDate} onChange={(e) => setFilterDate(e.target.value)} />
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">Tous les statuts</option>
            <option value="scheduled">Planifié</option>
            <option value="open">Ouvert</option>
            <option value="in_progress">En cours</option>
            <option value="closed">Terminé</option>
            <option value="cancelled">Annulé</option>
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Établissement</th>
              <th>Statut</th>
              <th>Présents (temps réel)</th>
            </tr>
          </thead>
          <tbody>
            {filteredSessions.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.exam_date} {s.start_time}
                </td>
                <td>{etablissements.find((e) => e.id === s.etablissement_id)?.name ?? "—"}</td>
                <td>
                  <ScheduleStatusBadge status={s.status} />
                </td>
                <td>
                  {s.status === "in_progress"
                    ? `${presentCounts[s.id] ?? 0}${s.nb_postes ? ` / ${s.nb_postes}` : ""}`
                    : "—"}
                </td>
              </tr>
            ))}
            {filteredSessions.length === 0 && (
              <tr>
                <td colSpan={4}>Aucune session pour ces filtres.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
