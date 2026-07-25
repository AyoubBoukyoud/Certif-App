import { useState, type FormEvent } from "react";
import { Modal } from "./Modal";
import type { Database } from "../lib/database.types";

type ExamSchedule = Database["public"]["Tables"]["exam_schedules"]["Row"];

export interface CandidateFormValues {
  cin: string;
  lastName: string;
  firstName: string;
  nomArabe: string;
  prenomArabe: string;
  sexe: string;
  birthDate: string;
  phone: string;
  filiere: string;
  groupe: string;
  examScheduleId: string;
}

export const EMPTY_CANDIDATE_FORM: CandidateFormValues = {
  cin: "",
  lastName: "",
  firstName: "",
  nomArabe: "",
  prenomArabe: "",
  sexe: "",
  birthDate: "",
  phone: "",
  filiere: "",
  groupe: "",
  examScheduleId: "",
};

/** Manual single-candidate add/edit form — the bulk Excel import (30
 * colonnes) remains the path for full-fidelity batch entry; this covers the
 * core fields worth editing one at a time. */
export function CandidateFormModal({
  title,
  initialValues,
  sessions,
  busy,
  onSubmit,
  onClose,
}: {
  title: string;
  initialValues: CandidateFormValues;
  sessions: ExamSchedule[];
  busy: boolean;
  onSubmit: (values: CandidateFormValues) => void;
  onClose: () => void;
}) {
  const [values, setValues] = useState(initialValues);

  function set<K extends keyof CandidateFormValues>(key: K, value: CandidateFormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit(values);
  }

  return (
    <Modal title={title} onClose={onClose}>
      <form className="inline-form" onSubmit={handleSubmit} style={{ flexDirection: "column" }}>
        <input
          placeholder="CIN"
          value={values.cin}
          onChange={(e) => set("cin", e.target.value.toUpperCase())}
          required
        />
        <input
          placeholder="Nom"
          value={values.lastName}
          onChange={(e) => set("lastName", e.target.value)}
          required
        />
        <input
          placeholder="Prénom"
          value={values.firstName}
          onChange={(e) => set("firstName", e.target.value)}
          required
        />
        <input
          placeholder="Nom (arabe)"
          value={values.nomArabe}
          onChange={(e) => set("nomArabe", e.target.value)}
        />
        <input
          placeholder="Prénom (arabe)"
          value={values.prenomArabe}
          onChange={(e) => set("prenomArabe", e.target.value)}
        />
        <select value={values.sexe} onChange={(e) => set("sexe", e.target.value)}>
          <option value="">Sexe…</option>
          <option value="M">M</option>
          <option value="F">F</option>
        </select>
        <input
          type="date"
          value={values.birthDate}
          onChange={(e) => set("birthDate", e.target.value)}
        />
        <input
          placeholder="Téléphone"
          value={values.phone}
          onChange={(e) => set("phone", e.target.value)}
        />
        <input
          placeholder="Filière"
          value={values.filiere}
          onChange={(e) => set("filiere", e.target.value)}
        />
        <input
          placeholder="Groupe"
          value={values.groupe}
          onChange={(e) => set("groupe", e.target.value)}
        />
        <select value={values.examScheduleId} onChange={(e) => set("examScheduleId", e.target.value)}>
          <option value="">Session d'examen (optionnel)…</option>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.exam_date} {s.start_time}
            </option>
          ))}
        </select>
        <button type="submit" disabled={busy}>
          {busy ? "Enregistrement…" : "Enregistrer"}
        </button>
      </form>
    </Modal>
  );
}
