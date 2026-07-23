import { useState, type FormEvent } from "react";
import { Modal } from "./Modal";

/** Generic "modifier les informations" modal for a managed account — full
 * name + login email always, plus the underlying entity's name (complexe /
 * établissement) when `entityLabel` is given (omit it for régionale and
 * surveillant, which have no separately-named entity to rename). */
export function AccountEditModal({
  title,
  initialFullName,
  initialEmail,
  initialEntityName,
  entityLabel,
  busy,
  onSubmit,
  onClose,
}: {
  title: string;
  initialFullName: string;
  initialEmail: string;
  initialEntityName?: string;
  entityLabel?: string;
  busy: boolean;
  onSubmit: (values: { fullName: string; email: string; entityName?: string }) => void;
  onClose: () => void;
}) {
  const [fullName, setFullName] = useState(initialFullName);
  const [email, setEmail] = useState(initialEmail);
  const [entityName, setEntityName] = useState(initialEntityName ?? "");
  const hasEntity = initialEntityName !== undefined;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ fullName, email, entityName: hasEntity ? entityName : undefined });
  }

  return (
    <Modal title={title} onClose={onClose}>
      <form className="inline-form" onSubmit={handleSubmit} style={{ flexDirection: "column" }}>
        <input
          placeholder="Nom complet"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />
        {hasEntity && (
          <input
            placeholder={entityLabel ?? "Nom"}
            value={entityName}
            onChange={(e) => setEntityName(e.target.value)}
            required
          />
        )}
        <input
          type="email"
          placeholder="Email (login)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <button type="submit" disabled={busy}>
          {busy ? "Enregistrement…" : "Enregistrer"}
        </button>
      </form>
    </Modal>
  );
}
