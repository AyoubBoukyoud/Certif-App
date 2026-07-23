import type { Database } from "./database.types";

type CandidateInsert = Database["public"]["Tables"]["candidates"]["Insert"];

// Excel header -> candidates column, per PROMPT_DASHBOARD_WEB.md §4.1.
// Matched case/accent/separator-insensitively (see `normalizeHeader`) so
// small variations in the source file ("CIN", "cin", "N° CIN") still hit.
const COL_MAP: Record<string, keyof CandidateInsert> = {
  cin: "cin",
  nom: "last_name",
  prenom: "first_name",
  nomarabe: "nom_arabe",
  prenomarabe: "prenom_arabe",
  datenaissance: "birth_date",
  sexe: "sexe",
  lieunaissance: "lieu_naissance",
  matriculeetudiant: "matricule_etudiant",
  diplome: "diplome",
  codediplome: "code_diplome",
  libellelong: "libelle_long",
  principale: "principale",
  code: "code",
  codediplome1: "codediplome1",
  niveauscolaire: "niveau_scolaire",
  anneeetude: "annee_etude",
  etudiantactif: "etudiant_actif",
  etudiantpayant: "etudiant_payant",
  regimeinscription: "regime_inscription",
  dateinscription: "date_inscription",
  datedossiercomplet: "date_dossier_complet",
  motifadmission: "motif_admission",
  site: "site",
  prenom2: "prenom2",
  ntelelephone: "phone",
  nteldututeur: "n_tel_tuteur",
  adresse: "adresse",
  nationalite: "nationalite",
  idinscriptionsessionprogramme: "id_inscription_session",
};

const BOOLEAN_FIELDS = new Set<keyof CandidateInsert>(["etudiant_actif", "etudiant_payant"]);
const DATE_FIELDS = new Set<keyof CandidateInsert>([
  "birth_date",
  "date_inscription",
  "date_dossier_complet",
]);

const COMBINING_MARKS_RE = new RegExp("[\\u0300-\\u036f]", "g");

function normalizeHeader(header: string): string {
  return header
    .normalize("NFD")
    .replace(COMBINING_MARKS_RE, "") // strip combining accents left by NFD
    .replace(/[^a-zA-Z0-9]/g, "")
    .toLowerCase();
}

function parseBoolean(value: unknown): boolean | null {
  if (value === null || value === undefined || value === "") return null;
  const s = String(value).trim().toLowerCase();
  if (["oui", "yes", "true", "1", "actif", "payant"].includes(s)) return true;
  if (["non", "no", "false", "0", "inactif", "non payant"].includes(s)) return false;
  return null;
}

/** Accepts DD/MM/YYYY or YYYY-MM-DD (per §4.1), returns YYYY-MM-DD or null. */
function parseDateCell(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  const s = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) {
    const [, d, mo, y] = m;
    return `${y}-${mo.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  return null;
}

export interface ImportRowResult {
  row: number; // 1-based, header excluded (matches the spreadsheet's data row order)
  outcome: "inserted" | "duplicate" | "error";
  message?: string;
  candidate?: CandidateInsert;
}

/** Builds the mapped candidate rows plus a per-row report. Duplicate
 * detection against `existingCins` (already-imported CIN for this
 * établissement) — actual insert happens separately in one batch call. */
export function mapExcelRows(
  rawRows: Record<string, unknown>[],
  opts: { etablissementId: string; examScheduleId: string | null; existingCins: Set<string> }
): { results: ImportRowResult[]; toInsert: CandidateInsert[] } {
  const results: ImportRowResult[] = [];
  const toInsert: CandidateInsert[] = [];
  const seenInBatch = new Set<string>();

  rawRows.forEach((raw, idx) => {
    const rowNum = idx + 1;
    const mapped: Partial<CandidateInsert> = {};

    for (const [header, rawValue] of Object.entries(raw)) {
      const field = COL_MAP[normalizeHeader(header)];
      if (!field) continue;
      if (rawValue === null || rawValue === undefined || rawValue === "") continue;

      if (BOOLEAN_FIELDS.has(field)) {
        (mapped as Record<string, unknown>)[field] = parseBoolean(rawValue);
      } else if (DATE_FIELDS.has(field)) {
        (mapped as Record<string, unknown>)[field] = parseDateCell(rawValue);
      } else {
        (mapped as Record<string, unknown>)[field] = String(rawValue).trim();
      }
    }

    const cin = (mapped.cin ?? "").toString().trim().toUpperCase();
    if (!cin) {
      results.push({ row: rowNum, outcome: "error", message: "CIN manquant." });
      return;
    }
    if (!mapped.last_name || !mapped.first_name) {
      results.push({ row: rowNum, outcome: "error", message: "Nom ou prénom manquant." });
      return;
    }
    if (opts.existingCins.has(cin) || seenInBatch.has(cin)) {
      results.push({ row: rowNum, outcome: "duplicate", message: `CIN ${cin} déjà présent.` });
      return;
    }

    seenInBatch.add(cin);
    const candidate: CandidateInsert = {
      ...mapped,
      cin,
      first_name: String(mapped.first_name),
      last_name: String(mapped.last_name),
      etablissement_id: opts.etablissementId,
      exam_schedule_id: opts.examScheduleId,
    };
    toInsert.push(candidate);
    results.push({ row: rowNum, outcome: "inserted", candidate });
  });

  return { results, toInsert };
}
