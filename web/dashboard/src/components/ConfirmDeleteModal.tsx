import { useState } from "react";
import { Modal } from "./Modal";
import { IconTrash } from "./icons";

/** Stronger confirmation than window.confirm() for cascading deletes — the
 * caller must retype the entity's exact name before "Supprimer" enables.
 * Used where deleting one row now wipes an entire subtree (complexe ->
 * établissements -> candidats/surveillants/sessions, or établissement ->
 * candidats/surveillants/sessions — see 0006_cascade_deletes.sql). */
export function ConfirmDeleteModal({
  title,
  entityName,
  warning,
  busy,
  onConfirm,
  onClose,
}: {
  title: string;
  entityName: string;
  warning: string;
  busy: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const [typed, setTyped] = useState("");
  const matches = typed.trim() === entityName;

  return (
    <Modal title={title} onClose={onClose}>
      <p className="error-banner">{warning}</p>
      <p>
        Cette action est <strong>irréversible</strong>. Pour confirmer, tapez le nom exact «{" "}
        <strong>{entityName}</strong> » ci-dessous :
      </p>
      <input
        value={typed}
        onChange={(e) => setTyped(e.target.value)}
        placeholder={entityName}
        autoFocus
      />
      <div style={{ marginTop: 16, display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button onClick={onClose}>Annuler</button>
        <button className="danger btn-icon-label" disabled={!matches || busy} onClick={onConfirm}>
          <IconTrash size={14} /> {busy ? "Suppression…" : "Supprimer définitivement"}
        </button>
      </div>
    </Modal>
  );
}
