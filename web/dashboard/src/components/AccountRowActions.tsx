import { IconEye, IconPencil, IconBan, IconCheckCircle, IconKey, IconTrash } from "./icons";

/** The five account-management actions (voir / modifier / activer-désactiver
 * / mot de passe / supprimer) as an icon row — shared by every dashboard
 * level that manages the accounts one level below it (National -> Régionale,
 * Régionale -> Complexe, Complexe -> Établissement, Établissement ->
 * Surveillant), all backed by the same manage-user Edge Function actions. */
export function AccountRowActions({
  isActive,
  busy,
  onView,
  onEdit,
  onToggle,
  onResetPassword,
  onDelete,
}: {
  isActive: boolean;
  busy: boolean;
  onView: () => void;
  onEdit: () => void;
  onToggle: () => void;
  onResetPassword: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="row-actions icon-actions">
      <button disabled={busy} onClick={onView} title="Voir les informations complètes" aria-label="Voir">
        <IconEye size={16} />
      </button>
      <button disabled={busy} onClick={onEdit} title="Modifier les informations" aria-label="Modifier">
        <IconPencil size={16} />
      </button>
      <button
        disabled={busy}
        onClick={onToggle}
        title={isActive ? "Désactiver" : "Activer"}
        aria-label={isActive ? "Désactiver" : "Activer"}
      >
        {isActive ? <IconBan size={16} /> : <IconCheckCircle size={16} />}
      </button>
      <button
        disabled={busy}
        onClick={onResetPassword}
        title="Réinitialiser le mot de passe"
        aria-label="Réinitialiser le mot de passe"
      >
        <IconKey size={16} />
      </button>
      <button
        disabled={busy}
        onClick={onDelete}
        title="Supprimer le compte"
        aria-label="Supprimer"
        className="danger"
      >
        <IconTrash size={16} />
      </button>
    </div>
  );
}
