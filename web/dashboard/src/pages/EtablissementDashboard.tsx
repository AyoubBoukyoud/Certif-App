import { useEffect, useLayoutEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import * as XLSX from "xlsx";
import { useAuth } from "../lib/AuthContext";
import { supabase } from "../lib/supabaseClient";
import type { CandidateManualStatus, Database } from "../lib/database.types";
import { mapExcelRows, type ImportRowResult } from "../lib/excelImport";
import { ImportReport } from "../components/ImportReport";
import { CandidateStatusBadge, ActiveStatusBadge, candidateStatusBadgeProps } from "../components/StatusBadge";
import { CandidateDetailModal } from "../components/CandidateDetailModal";
import {
  CandidateFormModal,
  EMPTY_CANDIDATE_FORM,
  type CandidateFormValues,
} from "../components/CandidateFormModal";
import { Modal } from "../components/Modal";
import { AccountRowActions } from "../components/AccountRowActions";
import { AccountDetailModal } from "../components/AccountDetailModal";
import { AccountEditModal } from "../components/AccountEditModal";
import { IconPlus, IconEye, IconPencil, IconTrash } from "../components/icons";
import { createAccount, toggleActive, resetPassword, updateAccount, deleteAccount } from "../lib/manageUser";
import { usePersistentState } from "../lib/usePersistentState";
import { readCache, writeCache } from "../lib/dataCache";

type ExamSchedule = Database["public"]["Tables"]["exam_schedules"]["Row"];
type Candidate = Database["public"]["Tables"]["candidates"]["Row"];
type Profile = Database["public"]["Tables"]["profiles"]["Row"];
type Etablissement = Database["public"]["Tables"]["etablissements"]["Row"];

interface CandidateWithAttempts extends Candidate {
  exam_sessions: Array<{ id: string; passed: boolean | null; score_pct: number | null; status: string; started_at: string | null }>;
}

interface CachedEtabData {
  sessions: ExamSchedule[];
  candidates: CandidateWithAttempts[];
  surveillants: Profile[];
  etablissementName: string;
}

const etabCacheKey = (etablissementId: string) => `etab-dash:data:${etablissementId}`;

function candidateToFormValues(c: Candidate): CandidateFormValues {
  return {
    cin: c.cin,
    lastName: c.last_name,
    firstName: c.first_name,
    nomArabe: c.nom_arabe ?? "",
    prenomArabe: c.prenom_arabe ?? "",
    sexe: c.sexe ?? "",
    birthDate: c.birth_date ?? "",
    phone: c.phone ?? "",
    filiere: c.filiere ?? "",
    groupe: c.groupe ?? "",
    examScheduleId: c.exam_schedule_id ?? "",
  };
}

const PAGE_SIZE = 10;
const STATUS_FILTERS = [
  { value: "", label: "Tous les statuts" },
  { value: "valide", label: "Validé" },
  { value: "en_cours", label: "En cours" },
  { value: "en_attente", label: "En attente" },
];

const STATUS_OPTIONS: Array<{ value: CandidateManualStatus | ""; label: string }> = [
  { value: "", label: "Auto (calculé)" },
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
  const [selectedEtabId, setSelectedEtabId] = usePersistentState("etab-dash:selectedEtabId", "");
  const etablissementId = isNational ? selectedEtabId : profile?.etablissement_id ?? "";

  // Lazily hydrated from the module-level cache (see lib/dataCache) so a
  // remount — e.g. clicking to another sidebar page and back — repaints the
  // last known data immediately instead of an empty table; refresh() below
  // still runs every mount to keep it current, it just no longer has to
  // pass through a visible empty state first.
  const cached = readCache<CachedEtabData>(etabCacheKey(etablissementId));
  const [sessions, setSessions] = useState<ExamSchedule[]>(cached?.sessions ?? []);
  const [candidates, setCandidates] = useState<CandidateWithAttempts[]>(cached?.candidates ?? []);
  const [surveillants, setSurveillants] = useState<Profile[]>(cached?.surveillants ?? []);
  const [etablissementName, setEtablissementName] = useState(cached?.etablissementName ?? "");
  const [sessionId, setSessionId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [importing, setImporting] = useState(false);
  const [importResults, setImportResults] = useState<ImportRowResult[] | null>(null);

  const [search, setSearch] = usePersistentState("etab-dash:search", "");
  const [statusFilter, setStatusFilter] = usePersistentState("etab-dash:statusFilter", "");
  const [page, setPage] = usePersistentState("etab-dash:page", 1);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [showNewCandidate, setShowNewCandidate] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState<CandidateWithAttempts | null>(null);

  const [showNewSurveillant, setShowNewSurveillant] = useState(false);
  const [newSvName, setNewSvName] = useState("");
  const [newSvEmail, setNewSvEmail] = useState("");
  const [newSvPassword, setNewSvPassword] = useState("");
  const [newSvAllEtab, setNewSvAllEtab] = useState(false);

  const [viewingSurveillant, setViewingSurveillant] = useState<Profile | null>(null);
  const [editingSurveillant, setEditingSurveillant] = useState<Profile | null>(null);

  async function refresh() {
    if (!etablissementId) return;
    const [s, c, et, sv, roamingSv] = await Promise.all([
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
      // Roaming surveillants (etablissement_id null = "tous établissements", see
      // 0005_surveillant_all_etablissements.sql) never match the .eq() above —
      // fetch them separately (national-only, since only national can create
      // one) so they still show up and stay manageable from this page.
      isNational
        ? supabase.from("profiles").select("*").eq("role", "surveillant").is("etablissement_id", null)
        : Promise.resolve({ data: [] as Profile[], error: null }),
    ]);
    if (s.error || c.error) {
      setError(s.error?.message ?? c.error?.message ?? "Erreur");
      return;
    }
    const nextSessions = s.data ?? [];
    const nextCandidates = (c.data as unknown as CandidateWithAttempts[]) ?? [];
    const nextEtablissementName = et.data?.name ?? "";
    const nextSurveillants = [...(sv.data ?? []), ...(roamingSv.data ?? [])];
    setSessions(nextSessions);
    setCandidates(nextCandidates);
    setEtablissementName(nextEtablissementName);
    setSurveillants(nextSurveillants);
    writeCache<CachedEtabData>(etabCacheKey(etablissementId), {
      sessions: nextSessions,
      candidates: nextCandidates,
      surveillants: nextSurveillants,
      etablissementName: nextEtablissementName,
    });
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

  // useLayoutEffect (not useEffect) so a switch of etablissementId (national
  // picking a different établissement mid-session) repaints from that id's
  // cached snapshot — or clears to empty if never visited — before the
  // browser paints, instead of flashing the previous établissement's data
  // for a frame. refresh() then updates it underneath with the live fetch.
  useLayoutEffect(() => {
    if (!etablissementId) return;
    const snapshot = readCache<CachedEtabData>(etabCacheKey(etablissementId));
    setSessions(snapshot?.sessions ?? []);
    setCandidates(snapshot?.candidates ?? []);
    setSurveillants(snapshot?.surveillants ?? []);
    setEtablissementName(snapshot?.etablissementName ?? "");
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

  async function onCreateCandidateSubmit(values: CandidateFormValues) {
    setError(null);
    setBusy(true);
    const { error } = await supabase.from("candidates").insert({
      etablissement_id: etablissementId,
      cin: values.cin.trim().toUpperCase(),
      last_name: values.lastName.trim(),
      first_name: values.firstName.trim(),
      nom_arabe: values.nomArabe || null,
      prenom_arabe: values.prenomArabe || null,
      sexe: values.sexe || null,
      birth_date: values.birthDate || null,
      phone: values.phone || null,
      filiere: values.filiere || null,
      groupe: values.groupe || null,
      exam_schedule_id: values.examScheduleId || null,
    });
    setBusy(false);
    if (error) {
      setError(error.message);
      return;
    }
    setShowNewCandidate(false);
    refresh();
  }

  async function onEditCandidateSubmit(values: CandidateFormValues) {
    if (!editingCandidate) return;
    setError(null);
    setBusy(true);
    const { error } = await supabase
      .from("candidates")
      .update({
        cin: values.cin.trim().toUpperCase(),
        last_name: values.lastName.trim(),
        first_name: values.firstName.trim(),
        nom_arabe: values.nomArabe || null,
        prenom_arabe: values.prenomArabe || null,
        sexe: values.sexe || null,
        birth_date: values.birthDate || null,
        phone: values.phone || null,
        filiere: values.filiere || null,
        groupe: values.groupe || null,
        exam_schedule_id: values.examScheduleId || null,
      })
      .eq("id", editingCandidate.id);
    setBusy(false);
    if (error) {
      setError(error.message);
      return;
    }
    setEditingCandidate(null);
    refresh();
  }

  async function onChangeCandidateStatus(c: CandidateWithAttempts, status: CandidateManualStatus | "") {
    setError(null);
    setBusy(true);
    const { error } = await supabase
      .from("candidates")
      .update({ status: status || null })
      .eq("id", c.id);
    setBusy(false);
    if (error) setError(error.message);
    else refresh();
  }

  async function onDeleteCandidate(c: CandidateWithAttempts) {
    if (c.exam_sessions.length > 0) {
      setError("Impossible de supprimer : ce candidat a des tentatives d'examen enregistrées.");
      return;
    }
    if (!window.confirm(`Supprimer définitivement le candidat ${c.first_name} ${c.last_name} ?`)) return;
    setBusy(true);
    const { error } = await supabase.from("candidates").delete().eq("id", c.id);
    setBusy(false);
    if (error) setError(error.message);
    else refresh();
  }

  const filteredCandidates = useMemo(() => {
    const q = search.trim().toLowerCase();
    return candidates.filter((c) => {
      if (q) {
        const hay = `${c.cin} ${c.first_name} ${c.last_name}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (statusFilter) {
        const { tone } = candidateStatusBadgeProps(c.exam_sessions, c.status as CandidateManualStatus | null);
        const bucket = tone === "good" ? "valide" : tone === "warning" ? "en_cours" : "en_attente";
        if (bucket !== statusFilter) return false;
      }
      return true;
    });
  }, [candidates, search, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / PAGE_SIZE));
  // page is persisted across visits (usePersistentState) — clamp it in case
  // the candidate list shrank since the last time this page was open.
  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages, setPage]);
  const pageCandidates = filteredCandidates.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  async function onCreateSurveillant(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const roaming = isNational && newSvAllEtab;
    const { error } = await createAccount({
      role: "surveillant",
      email: newSvEmail,
      password: newSvPassword,
      fullName: newSvName,
      etablissementId: roaming ? undefined : isNational ? etablissementId : undefined,
      allEtablissements: roaming,
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
    setNewSvAllEtab(false);
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
          <button className="btn-icon-label" onClick={() => setShowNewCandidate(true)}>
            <IconPlus size={14} /> Nouveau stagiaire
          </button>
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
                  <div className="row-actions">
                    <CandidateStatusBadge
                      attempts={c.exam_sessions}
                      manualStatus={c.status as CandidateManualStatus | null}
                    />
                    <select
                      aria-label={`Changer le statut de ${c.first_name} ${c.last_name}`}
                      value={c.status ?? ""}
                      disabled={busy}
                      onChange={(e) => onChangeCandidateStatus(c, e.target.value as CandidateManualStatus | "")}
                    >
                      {STATUS_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </td>
                <td>
                  <div className="row-actions">
                    <button
                      className="btn-icon-label"
                      onClick={() => setSelectedCandidate(c)}
                      aria-label="Voir le détail"
                    >
                      <IconEye size={14} /> Détail
                    </button>
                    <button onClick={() => setEditingCandidate(c)} title="Modifier" aria-label="Modifier">
                      <IconPencil size={14} />
                    </button>
                    <button
                      onClick={() => onDeleteCandidate(c)}
                      title="Supprimer"
                      aria-label="Supprimer"
                      className="danger"
                    >
                      <IconTrash size={14} />
                    </button>
                  </div>
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

      {showNewCandidate && (
        <CandidateFormModal
          title="Nouveau stagiaire"
          initialValues={EMPTY_CANDIDATE_FORM}
          sessions={sessions}
          busy={busy}
          onSubmit={onCreateCandidateSubmit}
          onClose={() => setShowNewCandidate(false)}
        />
      )}

      {editingCandidate && (
        <CandidateFormModal
          title={`Modifier — ${editingCandidate.first_name} ${editingCandidate.last_name}`}
          initialValues={candidateToFormValues(editingCandidate)}
          sessions={sessions}
          busy={busy}
          onSubmit={onEditCandidateSubmit}
          onClose={() => setEditingCandidate(null)}
        />
      )}

      <section className="card">
        <h2>Comptes surveillant</h2>
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Email</th>
              {isNational && <th>Portée</th>}
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {surveillants.map((sv) => (
              <tr key={sv.id}>
                <td>{sv.full_name}</td>
                <td>{sv.login ?? "—"}</td>
                {isNational && <td>{sv.etablissement_id === null ? "Tous établissements" : etablissementName}</td>}
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
                <td colSpan={isNational ? 5 : 4}>Aucun surveillant.</td>
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
            ["Établissement", viewingSurveillant.etablissement_id === null ? "Tous établissements" : etablissementName],
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
            {isNational && (
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  checked={newSvAllEtab}
                  onChange={(e) => setNewSvAllEtab(e.target.checked)}
                />
                Surveillant pour tous les établissements
              </label>
            )}
            <button type="submit" disabled={busy}>
              {busy ? "Création…" : "Créer"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
