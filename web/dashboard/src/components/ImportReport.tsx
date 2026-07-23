import type { ImportRowResult } from "../lib/excelImport";
import { IconCheck, IconAlertTriangle, IconXCircle } from "./icons";

export function ImportReport({ results }: { results: ImportRowResult[] }) {
  const inserted = results.filter((r) => r.outcome === "inserted").length;
  const duplicates = results.filter((r) => r.outcome === "duplicate").length;
  const errors = results.filter((r) => r.outcome === "error").length;

  return (
    <div>
      <p>
        {inserted} inséré(s) · {duplicates} doublon(s) ignoré(s) · {errors} erreur(s) — sur{" "}
        {results.length} ligne(s).
      </p>
      <div className="import-report">
        {results.map((r) => (
          <div
            key={r.row}
            className={
              "import-report-row" +
              (r.outcome === "error" ? " is-error" : r.outcome === "duplicate" ? " is-duplicate" : "")
            }
          >
            <span>Ligne {r.row}</span>
            <span className="import-report-outcome">
              {r.outcome === "inserted" && (
                <>
                  <IconCheck size={14} /> inséré
                </>
              )}
              {r.outcome === "duplicate" && (
                <>
                  <IconAlertTriangle size={14} /> doublon ignoré — {r.message ?? ""}
                </>
              )}
              {r.outcome === "error" && (
                <>
                  <IconXCircle size={14} /> erreur — {r.message ?? ""}
                </>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
