import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import type { Database } from "./database.types";

type Candidate = Database["public"]["Tables"]["candidates"]["Row"];
type ExamSession = Database["public"]["Tables"]["exam_sessions"]["Row"];

export function generateBilanPdf(
  candidate: Candidate,
  attempt: ExamSession,
  etablissementName: string,
  scheduleInfo?: { mos_version: string | null; exam_date: string | null }
) {
  const doc = new jsPDF();
  doc.setFontSize(16);
  doc.text("Bilan de certification MOS", 105, 20, { align: "center" });

  doc.setFontSize(11);
  doc.text(`Candidat : ${candidate.last_name} ${candidate.first_name}`, 20, 40);
  doc.text(`CIN : ${candidate.cin}`, 20, 48);
  doc.text(`Établissement : ${etablissementName}`, 20, 56);
  doc.text(
    `Date : ${attempt.started_at ? new Date(attempt.started_at).toLocaleDateString("fr-FR") : "—"}`,
    20,
    64
  );
  doc.text(`Version MOS : ${scheduleInfo?.mos_version ?? "—"}`, 20, 72);
  doc.text(`Score : ${attempt.score_pct != null ? attempt.score_pct.toFixed(1) : "—"}%`, 20, 80);
  doc.text(`Résultat : ${attempt.passed ? "RÉUSSI" : "ÉCHOUÉ"}`, 20, 88);

  const tasks = attempt.task_results ?? [];

  if (tasks.length > 0) {
    autoTable(doc, {
      startY: 100,
      head: [["N°", "Tâche", "Score", "Résultat"]],
      body: tasks.map((t) => [
        String(t.task_num ?? ""),
        t.title ?? "",
        `${Math.round((t.score ?? 0) * 100)}%`,
        t.passed ? "Réussi" : "Échoué",
      ]),
      styles: { fontSize: 10 },
    });
  }

  doc.save(`bilan_MOS_${candidate.cin}_${attempt.id.slice(0, 8)}.pdf`);
}
