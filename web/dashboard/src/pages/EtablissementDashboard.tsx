import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import * as XLSX from "xlsx";
import { useAuth } from "../lib/AuthContext";
import { supabase } from "../lib/supabaseClient";
import type { Database } from "../lib/database.types";
import { mapExcelRows, type ImportRowResult } from "../lib/excelImport";
import { ImportReport } from "../components/ImportReport";
import { CandidateStatusBadge, ActiveStatusBadge, candidateStatusBadgeProps } from "../components/StatusBadge";
import { CandidateDetailModal } from "../components/CandidateDetailModal";
import { Modal } from "../components/Modal";
import { AccountRowActions } from "../components/AccountRowActions";
import { AccountDetailModal } from "../components/AccountDetailModal";
import { AccountEditModal } from "../components/AccountEditModal";
import { IconPlus, IconEye } from "../components/icons";
import { createAccount, toggleActive, resetPassword, updateAccount, deleteAccount } from "../lib/manageUser";

type ExamSchedule = Database["public"]["Tables"]["exam_schedules"]["Row"];
type Candidate = Database["public"]["Tables"]["candidates"]["Row"];
type Profile = Database["public"]["Tables"]["profiles"]["Row"];
type Etablissement = Database["public"]["Tables"]["etablissements"]["Row"];

interface CandidateWithAttempts extends Candidate {
  exam_sessions: Array<{ id: string; passed: boolean | null; score_pct: number | null; status: string; started_at: string | null }>;
}

const PAGE_SIZE = 20;
const STATUS_FILTERS = [
  { value: "", label: "Tous les statuts" },
  { value: "valide", label: "Validé" },
  { value: "en_cours", label: "En cours" },
  { value: "en_attente", label: "En attente" },
];

export function EtablissementDashboard() {
  const { profile } = useAuth();
  // A 'national' caller has no etablissement_id of its own — it picks which
  // établissement to act for, from every établissement that exists.
  const isNational = profile?.role === "national";
  const [allEtablissements, setAllEtablissements] = useState<Etablissement[]>([]);
  const [selectedEtabId, setSelectedEtabId] = useState("");
  const etablissementId = isNational ? selectedEtabId : profile?.etablissement_id ?? "";

  const [sessions, setSessions] = useState<ExamSchedule[]>([]);
  const [candidates, setCandidates] = useState<CandidateWithAttempts[]>([]);
  const [surveillants, setSurveillants] = useState<Profile[]>([]);
  const [etablissementName, setEtablissementName] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [importing, setImporting] = useState(false);
  const [importResults, setImportResults] = useState<ImportRowResult[] | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);

  const [showNewSurveillant, setShowNewSurveillant] = useState(false);
  const [newSvName, setNewSvName] = useState("");
  const [newSvEmail, setNewSvEmail] = useState("");
  const [newSvPassword, setNewSvPassword] = useState("");

  const [viewingSurveillant, setViewingSurveillant] = useState<Profile | null>(null);
  const [editingSurveillant, setEditingSurveillant] = useState<Profile | null>(null);

  async function refresh() {
    if (!etablissementId) return;
    const [s, c, et, sv] = await Promise.all([
      supabase
        .from("exam_schedules")
        .select("*")
        .eq("etablissement_id", etablissementId)
        .order("exam_date", { ascending: false }),
      supabase
        .from("candidates")
        .select("*, exam_sessions(id, passed, score_pct, status, started_at)")
        .eq("etablissement_id", etablissementId)
        .order("last_name"),
      supabase.from("etablissements").select("name").eq("id", etablissementId).single(),
      supabase.from("profiles").select("*").eq("role", "surveillant").eq("etablissement_id", etablissementId),
    ]);
    if (s.error || c.error) {
      setError(s.error?.message ?? c.error?.message ?? "Erreur");
      return;
    }
    setSessions(s.data ?? []);
    setCandidates((c.data as unknown as CandidateWithAttempts[]) ?? []);
    setEtablissementName(et.data?.name ?? "");
    setSurveillants(sv.data ?? []);
  }

  // national only: load every établissement for the selector, defaulting to
  // the first one once available.
  useEffect(() => {
    if (!isNational) return;
    supabase
      .from("etablissements")
      .select("*")
      .order("name")
      .then(({ data }) => {
        setAllEtablissements(data ?? []);
        setSelectedEtabId((current) => current || data?.[0]?.id || "");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNational]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etablissementId]);

  async function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !etablissementId) return;

    setImporting(true);
    setError(null);
    setImportResults(null);
    try {
      const buf = await file.arrayBuffer();
      const wb = XLSX.read(buf, { type: "array" });
      const sheet = wb.Sheets[wb.SheetNames[0]];
      const rawRows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { raw: false });

      const existingCins = new Set(candidates.map((c) => c.cin));
      const { results, toInsert } = mapExcelRows(rawRows, {
        etablissementId,
        examScheduleId: sessionId || null,
        existingCins,
      });

      const { data: importRow, error: importError } = await supabase
        .from("excel_imports")
        .insert({
          etablissement_id: etablissementId,
          exam_schedule_id: sessionId || null,
          nom_fichier: file.name,
          nb_lignes: rawRows.length,
          nb_inseres: results.filter((r) => r.outcome === "inserted").length,
          nb_doublons: results.filter((r) => r.outcome === "duplicate").length,
          nb_erreurs: results.filter((r) => r.outcome === "error").length,
          statut: toInsert.length > 0 ? "termine" : "erreur",
          errors_json: results
            .filter((r) => r.outcome !== "inserted")
            .map((r) => ({ row: r.row, message: r.message ?? "" })),
          created_by: profile?.id,
        })
        .select()
        .single();
      if (importError) {
        setError(importError.message);
        return;
      }

      if (toInsert.length > 0) {
        const withBatch = toInsert.map((row) => ({ ...row, import_batch_id: importRow.id }));
        const { error: insertError } = await supabase.from("candidates").insert(withBatch);
        if (insertError) {
          setError(insertError.message);
          return;
        }
      }

      setImportResults(results);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la lecture du fichier.");
    } finally {
      setImporting(false);
    }
  }

  const filteredCandidates = useMemo(() => {
    const q = search.trim().toLowerCase();
    return candidates.filter((c) => {
      if (q) {
        const hay = `${c.cin} ${c.first_name} ${c.last_name}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (statusFilter) {
        const { tone } = candidateStatusBadgeProps(c.exam_sessions);
        const bucket = tone === "good" ? "valide" : tone === "warning" ? "en_cours" : "en_attente";
        if (bucket !== statusFilter) return false;
      }
      return true;
    });
  }, [candidates, search, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / PAGE_SIZE));
  const pageCandidates = filteredCandidates.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  async function onCreateSurveillant(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const { error } = await createAccount({
      role: "surveillant",
      email: newSvEmail,
      password: newSvPassword,
      fullName: newSvName,
      etablissementId: isNational ? etablissementId : undefined,
    });
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setShowNewSurveillant(false);
    setNewSvName("");
    setNewSvEmail("");
    setNewSvPassword("");
    refresh();
  }

  async function onToggleSurveillant(p: Profile) {
    setBusy(true);
    const { error } = await toggleActive(p.id, !p.is_active);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  async function onResetSurveillantPassword(p: Profile) {
    const pwd = window.prompt(`Nouveau mot de passe temporaire pour ${p.full_name} :`);
    if (!pwd) return;
    setBusy(true);
    const { error } = await resetPassword(p.id, pwd);
    setBusy(false);
    if (error) setError(error);
  }

  async function onEditSurveillantSubmit(values: { fullName: string; email: string }) {
    if (!editingSurveillant) return;
    setBusy(true);
    const { error } = await updateAccount(editingSurveillant.id, values);
    setBusy(false);
    if (error) {
      setError(error);
      return;
    }
    setEditingSurveillant(null);
    refresh();
  }

  async function onDeleteSurveillant(p: Profile) {
    if (!window.confirm(`Supprimer définitivement le compte de ${p.full_name} ?`)) return;
    setBusy(true);
    const { error } = await deleteAccount(p.id);
    setBusy(false);
    if (error) setError(error);
    else refresh();
  }

  return (
    <div>
      <h1>Mon établissement</h1>
      {isNational && (
        <div className="toolbar" style={{ marginBottom: "1rem" }}>
          <label htmlFor="etab-select">Établissement géré&nbsp;:</label>
          <select
            id="etab-select"
            value={selectedEtabId}
            onChange={(e) => setSelectedEtabId(e.target.value)}
          >
            {allEtablissements.length === 0 && <option value="">Aucun établissement</option>}
            {allEtablissements.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {error && <p className="error-banner">{error}</p>}

      <section className="card">
        <h2>Import de la liste des candidats</h2>
        <div className="inline-form">
          <select value={sessionId} onChange={(e) => setSessionId(e.target.value)}>
            <option value="">Session d'examen (optionnel)…</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.exam_date} {s.start_time}
              </option>
            ))}
          </select>
          <input type="file" accept=".xlsx,.xls,.csv" disabled={importing} onChange={onFileChange} />
        </div>
        <p className="hint">
          Fichier Excel 30 colonnes (CIN, Nom, Prenom, …). Un CIN déjà présent pour cet
          établissement est ignoré comme doublon.
        </p>
        {importing && <p className="hint">Import en cours…</p>}
        {importResults && <ImportReport results={importResults} />}
      </section>

      <section className="card">
        <h2>Candidats ({filteredCandidates.length})</h2>
        <div className="toolbar">
          <input
            type="search"
            placeholder="Recherche CIN ou nom…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          >
            {STATUS_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>CIN</th>
              <th>Nom</th>
              <th>Prénom</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pageCandidates.map((c) => (
              <tr key={c.id}>
                <td>{c.cin}</td>
                <td>{c.last_name}</td>
                <td>{c.first_name}</td>
                <td>
                  <CandidateStatusBadge attempts={c.exam_sessions} />
                </td>
                <td>
                  <button
                    className="btn-icon-label"
                    onClick={() => setSelectedCandidate(c)}
                    aria-label="Voir le détail"
                  >
                    <IconEye size={14} /> Détail
                  </button>
                </td>
              </tr>
            ))}
            {pageCandidates.length === 0 && (
              <tr>
                <td colSpan={5}>Aucun candidat.</td>
              </tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ‹ Précédent
            </button>
            <span>
              Page {page} / {totalPages}
            </span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Suivant ›
            </button>
          </div>
        )}
      </section>

      {selectedCandidate && (
        <CandidateDetailModal
          candidate={selectedCandidate}
          etablissementName={etablissementName}
          onClose={() => setSelectedCandidate(null)}
        />
      )}

      <section className="card">
        <h2>Comptes surveillant</h2>
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Email</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {surveillants.map((sv) => (
              <tr key={sv.id}>
                <td>{sv.full_name}</td>
                <td>{sv.login ?? "—"}</td>
                <td>
                  <ActiveStatusBadge isActive={sv.is_active} />
                </td>
                <td>
                  <AccountRowActions
                    isActive={sv.is_active}
                    busy={busy}
                    onView={() => setViewingSurveillant(sv)}
                    onEdit={() => setEditingSurveillant(sv)}
                    onToggle={() => onToggleSurveillant(sv)}
                    onResetPassword={() => onResetSurveillantPassword(sv)}
                    onDelete={() => onDeleteSurveillant(sv)}
                  />
                </td>
              </tr>
            ))}
            {surveillants.length === 0 && (
              <tr>
                <td colSpan={4}>Aucun surveillant.</td>
              </tr>
            )}
          </tbody>
        </table>
        <button className="btn-icon-label" onClick={() => setShowNewSurveillant(true)}>
          <IconPlus size={14} /> Nouveau surveillant
        </button>
      </section>

      {viewingSurveillant && (
        <AccountDetailModal
          title={viewingSurveillant.full_name}
          onClose={() => setViewingSurveillant(null)}
          fields={[
            ["Nom complet", viewingSurveillant.full_name],
            ["Email (login)", viewingSurveillant.login],
            ["Établissement", etablissementName],
            ["Statut", viewingSurveillant.is_active ? "Actif" : "Désactivé"],
            ["Créé le", new Date(viewingSurveillant.created_at).toLocaleString("fr-FR")],
          ]}
        />
      )}

      {editingSurveillant && (
        <AccountEditModal
          title={`Modifier — ${editingSurveillant.full_name}`}
          initialFullName={editingSurveillant.full_name}
          initialEmail={editingSurveillant.login ?? ""}
          busy={busy}
          onSubmit={onEditSurveillantSubmit}
          onClose={() => setEditingSurveillant(null)}
        />
      )}

      {showNewSurveillant && (
        <Modal title="Nouveau surveillant" onClose={() => setShowNewSurveillant(false)}>
          <form className="inline-form" onSubmit={onCreateSurveillant} style={{ flexDirection: "column" }}>
            <input
              placeholder="Nom complet"
              value={newSvName}
              onChange={(e) => setNewSvName(e.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email (login du compte SV)"
              value={newSvEmail}
              onChange={(e) => setNewSvEmail(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Mot de passe temporaire"
              value={newSvPassword}
              onChange={(e) => setNewSvPassword(e.target.value)}
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
