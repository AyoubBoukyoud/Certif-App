import { Modal } from "./Modal";

function formatValue(v: string | number | boolean | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Oui" : "Non";
  return String(v);
}

/** Generic "voir les informations complètes" modal for a managed account
 * (régionale / complexe / établissement / surveillant) — each caller passes
 * its own label/value pairs since the fields that matter differ per role. */
export function AccountDetailModal({
  title,
  fields,
  onClose,
}: {
  title: string;
  fields: Array<[string, string | number | boolean | null | undefined]>;
  onClose: () => void;
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="info-grid">
        {fields.map(([label, value]) => (
          <div key={label}>
            <span className="info-label">{label}</span>
            <span className="info-value">{formatValue(value)}</span>
          </div>
        ))}
      </div>
    </Modal>
  );
}
