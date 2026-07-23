import { useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import type { Database } from "../lib/database.types";
import { Modal } from "./Modal";
import { PDFBilanButton } from "./PDFBilanButton";

type Candidate = Database["public"]["Tables"]["candidates"]["Row"];
type ExamSession = Database["public"]["Tables"]["exam_sessions"]["Row"];

interface AttemptWithSchedule extends ExamSession {
  exam_schedules: { exam_date: string; start_time: string; mos_version: string | null } | null;
}

const INFO_FIELDS: Array<[keyof Candidate, string]> = [
  ["cin", "CIN"],
  ["last_name", "Nom"],
  ["first_name", "Prénom"],
  ["nom_arabe", "Nom (arabe)"],
  ["prenom_arabe", "Prénom (arabe)"],
  ["prenom2", "2ème prénom"],
  ["sexe", "Sexe"],
  ["birth_date", "Date de naissance"],
  ["lieu_naissance", "Lieu de naissance"],
  ["nationalite", "Nationalité"],
  ["phone", "Téléphone"],
  ["n_tel_tuteur", "Téléphone tuteur"],
  ["adresse", "Adresse"],
  ["matricule_etudiant", "Matricule étudiant"],
  ["diplome", "Diplôme"],
  ["code_diplome", "Code diplôme"],
  ["libelle_long", "Libellé long"],
  ["niveau_scolaire", "Niveau scolaire"],
  ["annee_etude", "Année d'étude"],
  ["filiere", "Filière"],
  ["groupe", "Groupe"],
  ["site", "Site"],
  ["regime_inscription", "Régime d'inscription"],
  ["date_inscription", "Date d'inscription"],
  ["date_dossier_complet", "Date dossier complet"],
  ["motif_admission", "Motif d'admission"],
  ["etudiant_actif", "Étudiant actif"],
  ["etudiant_payant", "Étudiant payant"],
];

function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Oui" : "Non";
  return String(v);
}

export function CandidateDetailModal({
  candidate,
  etablissementName,
  onClose,
}: {
  candidate: Candidate;
  etablissementName: string;
  onClose: () => void;
}) {
  const [attempts, setAttempts] = useState<AttemptWithSchedule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase
      .from("exam_sessions")
      .select("*, exam_schedules(exam_date, start_time, mos_version)")
      .eq("candidate_id", candidate.id)
      .order("started_at", { ascending: false })
      .then(({ data }) => {
        setAttempts((data as unknown as AttemptWithSchedule[]) ?? []);
        setLoading(false);
      });
  }, [candidate.id]);

  return (
    <Modal title={`${candidate.last_name} ${candidate.first_name}`} onClose={onClose} wide>
      <section>
        <h3>Informations personnelles</h3>
        <div className="info-grid">
          {INFO_FIELDS.map(([field, label]) => (
            <div key={String(field)}>
              <span className="info-label">{label}</span>
              <span className="info-value">{formatValue(candidate[field])}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3>Historique des examens</h3>
        {loading && <p className="hint">Chargement…</p>}
        {!loading && attempts.length === 0 && (
          <p className="hint">Aucune tentative enregistrée pour ce candidat.</p>
        )}
        {attempts.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Heure</th>
                <th>Version MOS</th>
                <th>Score</th>
                <th>Résultat</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {attempts.map((a) => (
                <tr key={a.id}>
                  <td>{a.exam_schedules?.exam_date ?? "—"}</td>
                  <td>{a.exam_schedules?.start_time ?? "—"}</td>
                  <td>{a.exam_schedules?.mos_version ?? "—"}</td>
                  <td>{a.score_pct != null ? `${a.score_pct.toFixed(1)}%` : "—"}</td>
                  <td>{a.passed === null ? "—" : a.passed ? "Réussi" : "Échoué"}</td>
                  <td>
                    {a.status === "terminated" ? (
                      <PDFBilanButton
                        candidate={candidate}
                        attempt={a}
                        etablissementName={etablissementName}
                        scheduleInfo={a.exam_schedules ?? undefined}
                      />
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </Modal>
  );
}
