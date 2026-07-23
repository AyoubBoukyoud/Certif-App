import { NavLink } from "react-router-dom";
import type { UserRole } from "../lib/database.types";
import { IconHome, IconBuilding, IconLandmark, IconGraduationCap, IconMonitor } from "./icons";
import type { ComponentType } from "react";

interface NavItem {
  to: string;
  label: string;
  Icon: ComponentType<{ size?: number }>;
}

const NAV_BY_ROLE: Record<UserRole, NavItem[]> = {
  // national is a super-admin: it can act as any Direction Régionale,
  // Complexe de Formation or Établissement, on top of its own read-only
  // national overview — so it gets every link, not just its own.
  national: [
    { to: "/national", label: "Vue nationale", Icon: IconHome },
    { to: "/regional", label: "Directions régionales", Icon: IconBuilding },
    { to: "/complexe", label: "Complexes", Icon: IconLandmark },
    { to: "/etablissement", label: "Établissements", Icon: IconGraduationCap },
  ],
  regional: [{ to: "/regional", label: "Ma région", Icon: IconBuilding }],
  complexe: [{ to: "/complexe", label: "Mon complexe", Icon: IconLandmark }],
  etablissement: [{ to: "/etablissement", label: "Mon établissement", Icon: IconGraduationCap }],
  surveillant: [{ to: "/surveillant", label: "Mes sessions", Icon: IconMonitor }],
};

export function Sidebar({ role }: { role: UserRole }) {
  const items = NAV_BY_ROLE[role];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">CA</span>
        <span className="sidebar-brand-name">Certif-App</span>
      </div>
      <nav className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
          >
            <span className="sidebar-icon" aria-hidden="true">
              <item.Icon size={18} />
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
