import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../lib/AuthContext";
import { supabase } from "../lib/supabaseClient";
import type { Database, ExamScheduleStatus } from "../lib/database.types";
import { StatTile } from "../components/charts/StatTile";
import { BarChart } from "../components/charts/BarChart";
import { Meter } from "../components/charts/Meter";
import { ScheduleStatusBadge, ActiveStatusBadge } from "../components/StatusBadge";
import { Modal } from "../components/Modal";
import { AccountRowActions } from "../components/AccountRowActions";
import { AccountDetailModal } from "../components/AccountDetailModal";
import { AccountEditModal } from "../components/AccountEditModal";
import { IconPlus } from "../components/icons";
import { createAccount, toggleActive, resetPassword, updateAccount, deleteAccount } from "../lib/manageUser";

type Complexe = Database["public"]["Tables"]["complexes"]["Row"];
type Etablissement = Database["public"]["Tables"]["etablissements"]["Row"];
type ExamSchedule = Database["public"]["Tables"]["exam_schedules"]["Row"];
type Profile = Database["public"]["Tables"]["profiles"]["Row"];
type Region = Database["public"]["Tables"]["regions"]["Row"];

const MOS_VERSIONS = ["Excel2016", "Word2016", "PPT2016", "ExcelExpert2016"];
const STATUS_OPTIONS: ExamScheduleStatus[] = ["scheduled", "open", "in_progress", "closed", "cancelled"];
const MONTH_FORMATTER = new Intl.DateTimeFormat("fr-FR", { month: "short", year: "numeric" });

export function RegionalDashboard() {
  const { profile } = useAuth();
  // A 'national' caller has no region_id of its own — it picks which region
  // to act as Direction Régionale for, from every region that exists.
  const isNational = profile?.role === "national";
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegionId, setSelectedRegionId] = useState("");
  const regionId = isNational ? selectedRegionId : profile?.region_id ?? "";

  const [complexes, setComplexes] = useState<Complexe[]>([]);
  const [complexeProfiles, setComplexeProfiles] = useState<Profile[]>([]);
  const [etablissements, setEtablissements] = useState<Etablissement[]>([]);
  const [sessions, setSessions] = useState<ExamSchedule[]>([]);
  const [candidatesCount, setCandidatesCount] = useState(0);
  const [passRate, setPassRate] = useState<{ pct: number | null; detail: string }>({
    pct: null,
    detail: "",
  });
  const [examsByMonth, setExamsByMonth] = useState<{ label: string; value: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [showNewComplexe, setShowNewComplexe] = useState(false);
  const [newComplexeName, setNewComplexeName] = useState("");
  const [newComplexeEmail, setNewComplexeEmail] = useState("");
  const [newComplexePassword, setNewComplexePassword] = useState("");

  const [viewingComplexe, setViewingComplexe] = useState<{ profile: Profile; complexe: Complexe } | null>(null);
  const [editingComplexe, setEditingComplexe] = useState<{ profile: Profile; complexe: Complexe } | null>(null);

  const [sessionEtabId, setSessionEtabId] = useState("");
  const [sessionDate, setSessionDate] = useState("");
  const [sessionTime, setSessionTime] = useState("09:00");
  const [sessionEndTime, setSessionEndTime] = useState("11:00");
  const [sessionVersion, setSessionVersion] = useState(MOS_VERSIONS[0]);
  const [sessionSeats, setSessionSeats] = useState("");
  const [sessionRoom, setSessionRoom] = useState("");

  async function refresh() {
    if (!regionId) return;
    // Two phases rather than one big Promise.all: the pass-rate query needs
    // this region's exam_schedule ids first, and a two-level dotted
    // embedded-resource filter (exam_schedules.etablissements.region_id)
    // isn't reliably supported — one level (etablissements!inner + .eq on
    // its column) is the documented/tested pattern, so stick to that.
    const [c, et, s] = await Promise.all([
      supabase.from("complexes").select("*").eq("region_id", regionId).order("name"),
      supabase.from("etablissements").select("*").eq("region_id", regionId).order("name"),
      supabase
        .from("exam_schedules")
        .select("*, etablissements!inner(region_id)")
        .eq("etablissements.region_id", regionId)
        .order("exam_date", { ascending: false }),
    ]);
    if (c.error || et.error || s.error) {
      setError(c.error?.message ?? et.error?.message ?? s.error?.message ?? "Erreur");
      return;
    }
    const scheduleRows = (s.data ?? []) as unknown as ExamSchedule[];
    setComplexes(c.data ?? []);
    setEtablissements(et.data ?? []);
    setSessions(scheduleRows);

    const scheduleIds = scheduleRows.map((row) => row.id);
    const [candCount, attempts] = await Promise.all([
      supabase
        .from("candidates")
        .select("id, etablissements!inner(region_id)", { count: "exact", head: true })
        .eq("etablissements.region_id", regionId),
      scheduleIds.length > 0
        ? supabase.from("exam_sessions").select("passed").in("exam_schedule_id", scheduleIds)
        : Promise.resolve({ data: [] as { passed: boolean | null }[], error: null }),
    ]);
    setCandidatesCount(candCount.count ?? 0);

    const graded = (attempts.data ?? []).filter((a) => a.passed !== null);
    const passedCount = graded.filter((a) => a.passed).length;
    setPassRate({
      pct: graded.length > 0 ? (passedCount / graded.length) * 100 : null,
      detail: `${passedCount}/${graded.length} candidats admis`,
    });

    const byMonth = new Map<string, number>();
    for (const sess of scheduleRows) {
      const label = MONTH_FORMATTER.format(new Date(sess.exam_date));
      byMonth.set(label, (byMonth.get(label) ?? 0) + 1);
    }
    setExamsByMonth(Array.from(byMonth.entries()).map(([label, value]) => ({ label, value })));

    if (c.data && c.data.length > 0) {
      const { data: profs } = await supabase
        .from("profiles")
        .select("*")
        .eq("role", "complexe")
        .in("complexe_id", c.data.map((row) => row.id));
      setComplexeProfiles(profs ?? []);
    } else {
      setComplexeProfiles([]);
    }
  }

  // national only: load every region for the selector, defaulting to the
  // first one once available.
  useEffect(() => {
    if (!isNational) return;
    supabase
      .from("regions")
      .select("*")
      .order("name")
      .then(({ data }) => {
        setRegions(data ?? []);
        setSelectedRegionId((current) => current || data?.[0]?.id || "");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNational]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regionId]);

  async function onCreateComplexe(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const { error } = await createAccount({
      role: "complexe",
      email: newComplexeEmail,
      password: newComplexePassword,
      fullName: newComplexeName,
      entityName: newComplexeName,
      regionId: isNational ? regionId : undefined,
    });
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setShowNewComplexe(false);
    setNewComplexeName("");
    setNewComplexeEmail("");
    setNewComplexePassword("");
    refresh();
  }

  async function onToggleComplexe(p: Profile) {
    setBusy(true);
    const { error } = await toggleActive(p.id, !p.is_active);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  async function onResetComplexePassword(p: Profile) {
    const pwd = window.prompt(`Nouveau mot de passe temporaire pour ${p.full_name} :`);
    if (!pwd) return;
    setBusy(true);
    const { error } = await resetPassword(p.id, pwd);
    setBusy(false);
    if (error) setError(error);
  }

  async function onEditComplexeSubmit(values: { fullName: string; email: string; entityName?: string }) {
    if (!editingComplexe) return;
    setBusy(true);
    const { error } = await updateAccount(editingComplexe.profile.id, values);
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setEditingComplexe(null);
    refresh();
  }

  async function onDeleteComplexe(p: Profile) {
    if (!window.confirm(`Supprimer définitivement le compte de ${p.full_name} ?`)) return;
    setBusy(true);
    const { error } = await deleteAccount(p.id);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  async function onScheduleSession(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!sessionEtabId || !sessionDate) {
      setError("Choisissez un établissement et une date.");
      return;
    }
    const { error } = await supabase.from("exam_schedules").insert({
      etablissement_id: sessionEtabId,
      exam_date: sessionDate,
      start_time: sessionTime,
      duration_minutes:
        sessionTime && sessionEndTime
          ? Math.max(
              0,
              (new Date(`1970-01-01T${sessionEndTime}`).getTime() -
                new Date(`1970-01-01T${sessionTime}`).getTime()) /
                60000
            )
          : null,
      mos_version: sessionVersion,
      nb_postes: sessionSeats ? Number(sessionSeats) : null,
      room: sessionRoom || null,
      created_by: profile?.id,
    });
    if (error) {
      setError(error.message);
      return;
    }
    setSessionDate("");
    setSessionSeats("");
    setSessionRoom("");
    refresh();
  }

  async function onChangeStatus(session: ExamSchedule, status: ExamScheduleStatus) {
    const { error } = await supabase
      .from("exam_schedules")
      .update({ status })
      .eq("id", session.id);
    if (error) setError(error.message);
    else refresh();
  }

  async function onDeleteSession(session: ExamSchedule) {
    if (session.status !== "scheduled") return;
    if (!window.confirm("Supprimer cette session planifiée ?")) return;
    const { error } = await supabase.from("exam_schedules").delete().eq("id", session.id);
    if (error) setError(error.message);
    else refresh();
  }

  const complexeProfileFor = (c: Complexe) => complexeProfiles.find((p) => p.complexe_id === c.id);
  const etabCountFor = (c: Complexe) => etablissements.filter((e) => e.complexe_id === c.id).length;

  return (
    <div>
      <h1>Ma région</h1>
      {isNational && (
        <div className="toolbar" style={{ marginBottom: "1rem" }}>
          <label htmlFor="region-select">Région gérée&nbsp;:</label>
          <select
            id="region-select"
            value={selectedRegionId}
            onChange={(e) => setSelectedRegionId(e.target.value)}
          >
            {regions.length === 0 && <option value="">Aucune région</option>}
            {regions.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {error && <p className="error-banner">{error}</p>}

      <div className="stat-row">
        <StatTile label="Complexes actifs" value={complexes.filter((c) => complexeProfileFor(c)?.is_active !== false).length} />
        <StatTile
          label="Examens ce mois"
          value={
            sessions.filter((s) => {
              const d = new Date(s.exam_date);
              const now = new Date();
              return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
            }).length
          }
        />
        <StatTile label="Candidats" value={candidatesCount} />
        <StatTile label="Établissements" value={etablissements.length} />
      </div>

      <div className="chart-grid">
        <section className="card">
          <h2>Examens par mois</h2>
          <BarChart data={examsByMonth} emptyMessage="Aucune session planifiée." />
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
        <section className="card">
          <h2>Activité récente</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Établissement</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 5).map((s) => (
                <tr key={s.id}>
                  <td>{s.exam_date}</td>
                  <td>{etablissements.find((e) => e.id === s.etablissement_id)?.name ?? "—"}</td>
                  <td>
                    <ScheduleStatusBadge status={s.status} />
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={3}>Aucune session.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>

      <section className="card">
        <h2>Complexes de Formation</h2>
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Établissements</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {complexes.map((c) => {
              const p = complexeProfileFor(c);
              return (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{etabCountFor(c)}</td>
                  <td>{p ? <ActiveStatusBadge isActive={p.is_active} /> : "—"}</td>
                  <td>
                    {p && (
                      <AccountRowActions
                        isActive={p.is_active}
                        busy={busy}
                        onView={() => setViewingComplexe({ profile: p, complexe: c })}
                        onEdit={() => setEditingComplexe({ profile: p, complexe: c })}
                        onToggle={() => onToggleComplexe(p)}
                        onResetPassword={() => onResetComplexePassword(p)}
                        onDelete={() => onDeleteComplexe(p)}
                      />
                    )}
                  </td>
                </tr>
              );
            })}
            {complexes.length === 0 && (
              <tr>
                <td colSpan={4}>Aucun complexe.</td>
              </tr>
            )}
          </tbody>
        </table>
        <button className="btn-icon-label" onClick={() => setShowNewComplexe(true)}>
          <IconPlus size={14} /> Nouveau complexe
        </button>
      </section>

      {viewingComplexe && (
        <AccountDetailModal
          title={viewingComplexe.complexe.name}
          onClose={() => setViewingComplexe(null)}
          fields={[
            ["Nom du complexe", viewingComplexe.complexe.name],
            ["Responsable", viewingComplexe.profile.full_name],
            ["Email (login)", viewingComplexe.profile.login],
            ["Établissements", etabCountFor(viewingComplexe.complexe)],
            ["Statut", viewingComplexe.profile.is_active ? "Actif" : "Désactivé"],
            ["Créé le", new Date(viewingComplexe.complexe.created_at).toLocaleString("fr-FR")],
          ]}
        />
      )}

      {editingComplexe && (
        <AccountEditModal
          title={`Modifier — ${editingComplexe.complexe.name}`}
          initialFullName={editingComplexe.profile.full_name}
          initialEmail={editingComplexe.profile.login ?? ""}
          initialEntityName={editingComplexe.complexe.name}
          entityLabel="Nom du complexe"
          busy={busy}
          onSubmit={onEditComplexeSubmit}
          onClose={() => setEditingComplexe(null)}
        />
      )}

      {showNewComplexe && (
        <Modal title="Nouveau complexe" onClose={() => setShowNewComplexe(false)}>
          <form className="inline-form" onSubmit={onCreateComplexe} style={{ flexDirection: "column" }}>
            <input
              placeholder="Nom du complexe"
              value={newComplexeName}
              onChange={(e) => setNewComplexeName(e.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email (login du compte CF)"
              value={newComplexeEmail}
              onChange={(e) => setNewComplexeEmail(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Mot de passe temporaire"
              value={newComplexePassword}
              onChange={(e) => setNewComplexePassword(e.target.value)}
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
        <h2>Sessions d'examen</h2>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Heure</th>
              <th>Établissement</th>
              <th>Version MOS</th>
              <th>Postes</th>
              <th>Salle</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>{s.exam_date}</td>
                <td>{s.start_time}</td>
                <td>{etablissements.find((e) => e.id === s.etablissement_id)?.name ?? "—"}</td>
                <td>{s.mos_version ?? "—"}</td>
                <td>{s.nb_postes ?? "—"}</td>
                <td>{s.room ?? "—"}</td>
                <td>
                  <select value={s.status} onChange={(e) => onChangeStatus(s, e.target.value as ExamScheduleStatus)}>
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="row-actions">
                  {s.status === "scheduled" && (
                    <button onClick={() => onDeleteSession(s)}>Supprimer</button>
                  )}
                </td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr>
                <td colSpan={8}>Aucune session planifiée.</td>
              </tr>
            )}
          </tbody>
        </table>

        <form className="inline-form" onSubmit={onScheduleSession}>
          <select value={sessionEtabId} onChange={(e) => setSessionEtabId(e.target.value)} required>
            <option value="">Établissement…</option>
            {etablissements.map((et) => (
              <option key={et.id} value={et.id}>
                {et.name}
              </option>
            ))}
          </select>
          <input type="date" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)} required />
          <input type="time" value={sessionTime} onChange={(e) => setSessionTime(e.target.value)} required />
          <input type="time" value={sessionEndTime} onChange={(e) => setSessionEndTime(e.target.value)} required />
          <select value={sessionVersion} onChange={(e) => setSessionVersion(e.target.value)}>
            {MOS_VERSIONS.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            placeholder="Nb postes"
            value={sessionSeats}
            onChange={(e) => setSessionSeats(e.target.value)}
          />
          <input placeholder="Salle" value={sessionRoom} onChange={(e) => setSessionRoom(e.target.value)} />
          <button type="submit">Planifier</button>
        </form>
      </section>
    </div>
  );
}
