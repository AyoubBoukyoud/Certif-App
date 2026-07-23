type MeterStatus = "good" | "warning" | "critical";

export function Meter({
  label,
  pct,
  detail,
  status = "good",
  emptyMessage,
}: {
  label: string;
  pct: number | null;
  detail?: string;
  status?: MeterStatus;
  emptyMessage?: string;
}) {
  const empty = pct === null;

  return (
    <div className="meter">
      <div className="meter-head">
        <span className="meter-label">{label}</span>
        <span className="meter-value">{empty ? "—" : `${Math.round(pct)}%`}</span>
      </div>
      <div className="meter-track">
        {!empty && (
          <div
            className={`meter-fill meter-fill-${status}`}
            style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
          />
        )}
      </div>
      {empty ? (
        <span className="hint">{emptyMessage ?? "Aucune donnée."}</span>
      ) : (
        detail && <span className="hint">{detail}</span>
      )}
    </div>
  );
}
