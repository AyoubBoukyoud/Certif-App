import type { ReactNode } from "react";
import { IconX } from "./icons";

export function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={"modal-card" + (wide ? " modal-wide" : "")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Fermer">
            <IconX size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
