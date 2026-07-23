import type { SVGProps } from "react";

/** Flat, single-color line icons (stroke = currentColor) used across the
 * dashboard, replacing emoji. One shared 24x24 stroke style so every icon
 * lines up regardless of which one is used — pass `size` to scale. */
type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 16, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export function IconHome(props: IconProps) {
  return (
    <Svg {...props}>
      <polyline points="4 11 12 4 20 11" />
      <path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9" />
    </Svg>
  );
}

/** Office building — used for "Directions régionales". */
export function IconBuilding(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="4" y="2" width="16" height="20" rx="1" />
      <rect x="8" y="6" width="2" height="2" />
      <rect x="14" y="6" width="2" height="2" />
      <rect x="8" y="11" width="2" height="2" />
      <rect x="14" y="11" width="2" height="2" />
      <rect x="10" y="16" width="4" height="6" />
    </Svg>
  );
}

/** Columned institution — used for "Complexes de Formation". */
export function IconLandmark(props: IconProps) {
  return (
    <Svg {...props}>
      <polygon points="12 3 21 9 3 9" />
      <line x1="3" y1="21" x2="21" y2="21" />
      <line x1="5" y1="21" x2="5" y2="10" />
      <line x1="9" y1="21" x2="9" y2="10" />
      <line x1="15" y1="21" x2="15" y2="10" />
      <line x1="19" y1="21" x2="19" y2="10" />
    </Svg>
  );
}

export function IconGraduationCap(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2 9 12 4l10 5-10 5-10-5Z" />
      <path d="M6 11.5v4c0 1.5 3 3 6 3s6-1.5 6-3v-4" />
      <line x1="21" y1="9" x2="21" y2="15" />
    </Svg>
  );
}

/** Desktop monitor — used for the surveillant's kiosk-session view. */
export function IconMonitor(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="4" width="18" height="12" rx="1" />
      <line x1="8" y1="20" x2="16" y2="20" />
      <line x1="12" y1="16" x2="12" y2="20" />
    </Svg>
  );
}

export function IconEye(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  );
}

export function IconPencil(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </Svg>
  );
}

/** Circle-slash — "désactiver". */
export function IconBan(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <line x1="5.5" y1="5.5" x2="18.5" y2="18.5" />
    </Svg>
  );
}

/** Circle-check — "activer". */
export function IconCheckCircle(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <polyline points="8 12 11 15 16 9" />
    </Svg>
  );
}

export function IconKey(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="14.5" r="3.5" />
      <line x1="10.5" y1="12" x2="20" y2="2.5" />
      <line x1="16.5" y1="6" x2="19" y2="8.5" />
    </Svg>
  );
}

export function IconTrash(props: IconProps) {
  return (
    <Svg {...props}>
      <polyline points="4 7 20 7" />
      <path d="M6 7V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2" />
      <path d="M6 7h12l-1 13a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2Z" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </Svg>
  );
}

export function IconPlus(props: IconProps) {
  return (
    <Svg {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Svg>
  );
}

export function IconX(props: IconProps) {
  return (
    <Svg {...props}>
      <line x1="6" y1="6" x2="18" y2="18" />
      <line x1="18" y1="6" x2="6" y2="18" />
    </Svg>
  );
}

export function IconBell(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 8a6 6 0 1 1 12 0c0 4 1.5 5.5 2 6.5H4c.5-1 2-2.5 2-6.5Z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </Svg>
  );
}

export function IconSun(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="4" />
      <line x1="12" y1="2" x2="12" y2="4.5" />
      <line x1="12" y1="19.5" x2="12" y2="22" />
      <line x1="2" y1="12" x2="4.5" y2="12" />
      <line x1="19.5" y1="12" x2="22" y2="12" />
      <line x1="4.9" y1="4.9" x2="6.6" y2="6.6" />
      <line x1="17.4" y1="17.4" x2="19.1" y2="19.1" />
      <line x1="4.9" y1="19.1" x2="6.6" y2="17.4" />
      <line x1="17.4" y1="6.6" x2="19.1" y2="4.9" />
    </Svg>
  );
}

export function IconMoon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />
    </Svg>
  );
}

export function IconCheck(props: IconProps) {
  return (
    <Svg {...props}>
      <polyline points="4 12 9 17 20 6" />
    </Svg>
  );
}

export function IconAlertTriangle(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3 2 20h20Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12" y2="17.01" />
    </Svg>
  );
}

export function IconXCircle(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <line x1="9" y1="9" x2="15" y2="15" />
      <line x1="15" y1="9" x2="9" y2="15" />
    </Svg>
  );
}
