import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../lib/AuthContext";
import { supabase } from "../lib/supabaseClient";
import type { Database } from "../lib/database.types";
import { StatTile } from "../components/charts/StatTile";
import { ScheduleStatusBadge } from "../components/StatusBadge";
import { Modal } from "../components/Modal";
import { useRealtimeTable } from "../hooks/useRealtimeTable";

type ExamSchedule = Database["public"]["Tables"]["exam_schedules"]["Row"];
type ExamSessionAttempt = Database["public"]["Tables"]["exam_sessions"]["Row"];

const todayIso = () => new Date().toISOString().slice(0, 10);
const INCIDENT_TYPES = ["Technique", "Comportement", "Absence", "Autre"];

export function SurveillantDashboard() {
  const { profile } = useAuth();
  const [schedules, setSchedules] = useState<ExamSchedule[]>([]);
  const [myAttemptsCount, setMyAttemptsCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [detailSchedule, setDetailSchedule] = useState<ExamSchedule | null>(null);
  const [detailAttempts, setDetailAttempts] = useState<ExamSessionAttempt[]>([]);
  const [showIncidentForm, setShowIncidentForm] = useState(false);
  const [incidentType, setIncidentType] = useState(INCIDENT_TYPES[0]);
  const [incidentDescription, setIncidentDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!profile?.etablissement_id) return;
    const [s, myAttempts] = await Promise.all([
      supabase
        .from("exam_schedules")
        .select("*")
        .eq("etablissement_id", profile.etablissement_id)
        .order("exam_date", { ascending: false }),
      supabase
        .from("exam_sessions")
        .select("id", { count: "exact", head: true })
        .eq("validated_by", profile.id),
    ]);
    if (s.error) {
      setError(s.error.message);
      return;
    }
    setSchedules(s.data ?? []);
    setMyAttemptsCount(myAttempts.count ?? 0);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.etablissement_id]);

  useRealtimeTable("exam_schedules", refresh);

  async function openDetail(schedule: ExamSchedule) {
    setDetailSchedule(schedule);
    setShowIncidentForm(false);
    const { data } = await supabase
      .from("exam_sessions")
      .select("*")
      .eq("exam_schedule_id", schedule.id)
      .order("started_at", { ascending: false });
    setDetailAttempts(data ?? []);
  }

  async function onSubmitIncident(e: FormEvent) {
    e.preventDefault();
    if (!detailSchedule || !profile) return;
    setBusy(true);
    setError(null);
    const { error } = await supabase.from("incident_reports").insert({
      type_incident: incidentType,
      description: incidentDescription,
      exam_schedule_id: detailSchedule.id,
      reported_by: profile.id,
    });
    setBusy(false);
    if (error) {
      setError(error.message);
      return;
    }
    setShowIncidentForm(false);
    setIncidentDescription("");
  }

  const todaySchedules = schedules.filter((s) => s.exam_date === todayIso());
  const nextSchedule = schedules
    .filter((s) => s.exam_date >= todayIso() && s.status !== "cancelled")
    .sort((a, b) => a.exam_date.localeCompare(b.exam_date))[0];

  return (
    <div>
      <h1>Mes sessions</h1>
      {error && <p className="error-banner">{error}</p>}

      <div className="stat-row">
        <StatTile label="Sessions aujourd'hui" value={todaySchedules.length} />
        <StatTile label="Prochaine session" value={nextSchedule ? nextSchedule.exam_date : "—"} />
        <StatTile label="Candidats validés (total)" value={myAttemptsCount} />
      </div>

      <section className="card">
        <h2>Sessions de mon établissement</h2>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Heure</th>
              <th>Version MOS</th>
              <th>Salle</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {schedules.map((s) => (
              <tr key={s.id}>
                <td>{s.exam_date}</td>
                <td>{s.start_time}</td>
                <td>{s.mos_version ?? "—"}</td>
                <td>{s.room ?? "—"}</td>
                <td>
                  <ScheduleStatusBadge status={s.status} />
                </td>
                <td>
                  <button onClick={() => openDetail(s)}>Détail</button>
                </td>
              </tr>
            ))}
            {schedules.length === 0 && (
              <tr>
                <td colSpan={6}>Aucune session pour votre établissement.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {detailSchedule && (
        <Modal
          title={`Session du ${detailSchedule.exam_date} — ${detailSchedule.start_time}`}
          onClose={() => setDetailSchedule(null)}
        >
          <h3>Candidats</h3>
          <table>
            <thead>
              <tr>
                <th>Statut</th>
                <th>Score</th>
                <th>Résultat</th>
              </tr>
            </thead>
            <tbody>
              {detailAttempts.map((a) => (
                <tr key={a.id}>
                  <td>{a.status}</td>
                  <td>{a.score_pct != null ? `${a.score_pct.toFixed(1)}%` : "—"}</td>
                  <td>{a.passed === null ? "—" : a.passed ? "Réussi" : "Échoué"}</td>
                </tr>
              ))}
              {detailAttempts.length === 0 && (
                <tr>
                  <td colSpan={3}>Aucun candidat pour cette session pour l'instant.</td>
                </tr>
              )}
            </tbody>
          </table>

          {!showIncidentForm && (
            <button style={{ marginTop: 14 }} onClick={() => setShowIncidentForm(true)}>
              Signaler un incident
            </button>
          )}
          {showIncidentForm && (
            <form className="inline-form" onSubmit={onSubmitIncident} style={{ flexDirection: "column", marginTop: 14 }}>
              <select value={incidentType} onChange={(e) => setIncidentType(e.target.value)}>
                {INCIDENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <textarea
                placeholder="Description de l'incident"
                value={incidentDescription}
                onChange={(e) => setIncidentDescription(e.target.value)}
                required
                rows={3}
              />
              <button type="submit" disabled={busy}>
                {busy ? "Envoi…" : "Envoyer le signalement"}
              </button>
            </form>
          )}
        </Modal>
      )}
    </div>
  );
}
