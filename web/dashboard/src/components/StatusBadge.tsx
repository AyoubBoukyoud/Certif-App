import type { ReactNode } from "react";
import type { CandidateManualStatus, ExamScheduleStatus, ExcelImportStatus } from "../lib/database.types";
import { IconCheck } from "./icons";

export type BadgeTone = "good" | "warning" | "critical" | "neutral";

export function Badge({ tone, label, icon }: { tone: BadgeTone; label: string; icon?: ReactNode }) {
  return (
    <span className={`badge badge-${tone}`}>
      {icon}
      {label}
    </span>
  );
}

const SCHEDULE_STATUS_LABELS: Record<ExamScheduleStatus, { label: string; tone: BadgeTone }> = {
  scheduled: { label: "Planifié", tone: "neutral" },
  open: { label: "Ouvert", tone: "good" },
  in_progress: { label: "En cours", tone: "warning" },
  closed: { label: "Terminé", tone: "neutral" },
  cancelled: { label: "Annulé", tone: "critical" },
};

export function ScheduleStatusBadge({ status }: { status: ExamScheduleStatus }) {
  const s = SCHEDULE_STATUS_LABELS[status] ?? { label: status, tone: "neutral" as BadgeTone };
  return <Badge tone={s.tone} label={s.label} />;
}

const IMPORT_STATUS_LABELS: Record<ExcelImportStatus, { label: string; tone: BadgeTone }> = {
  en_cours: { label: "En cours", tone: "warning" },
  termine: { label: "Terminé", tone: "good" },
  erreur: { label: "Erreur", tone: "critical" },
};

export function ImportStatusBadge({ status }: { status: ExcelImportStatus }) {
  const s = IMPORT_STATUS_LABELS[status] ?? { label: status, tone: "neutral" as BadgeTone };
  return <Badge tone={s.tone} label={s.label} />;
}

export function ActiveStatusBadge({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <Badge tone="good" label="Actif" />
  ) : (
    <Badge tone="critical" label="Désactivé" />
  );
}

const MANUAL_STATUS_LABELS: Record<CandidateManualStatus, { label: string; tone: BadgeTone }> = {
  valide: { label: "Validé", tone: "good" },
  en_cours: { label: "En cours", tone: "warning" },
  en_attente: { label: "En attente", tone: "neutral" },
};

/** Candidate status. Normally derived from their exam_sessions (attempts)
 * rows — "Validé" if any attempt passed, "En cours" if one is still running,
 * "En attente" otherwise (per PROMPT_DASHBOARD_WEB.md §4.2) — but a non-null
 * `manualStatus` (candidates.status, set from the dashboard) overrides it. */
export function candidateStatusBadgeProps(
  attempts: Array<{ passed: boolean | null; status: string }>,
  manualStatus?: CandidateManualStatus | null
): { label: string; tone: BadgeTone } {
  if (manualStatus) return MANUAL_STATUS_LABELS[manualStatus];
  if (attempts.some((a) => a.passed === true)) return { label: "Validé", tone: "good" };
  if (attempts.some((a) => a.status === "started")) return { label: "En cours", tone: "warning" };
  return { label: "En attente", tone: "neutral" };
}

export function CandidateStatusBadge({
  attempts,
  manualStatus,
}: {
  attempts: Array<{ passed: boolean | null; status: string }>;
  manualStatus?: CandidateManualStatus | null;
}) {
  const s = candidateStatusBadgeProps(attempts, manualStatus);
  return <Badge tone={s.tone} label={s.label} icon={s.tone === "good" ? <IconCheck size={11} /> : undefined} />;
}
