import type { Database } from "../lib/database.types";
import { generateBilanPdf } from "../lib/pdfBilan";

type Candidate = Database["public"]["Tables"]["candidates"]["Row"];
type ExamSession = Database["public"]["Tables"]["exam_sessions"]["Row"];

export function PDFBilanButton({
  candidate,
  attempt,
  etablissementName,
  scheduleInfo,
}: {
  candidate: Candidate;
  attempt: ExamSession;
  etablissementName: string;
  scheduleInfo?: { mos_version: string | null; exam_date: string | null };
}) {
  return (
    <button
      onClick={() => generateBilanPdf(candidate, attempt, etablissementName, scheduleInfo)}
    >
      Télécharger le bilan
    </button>
  );
}
