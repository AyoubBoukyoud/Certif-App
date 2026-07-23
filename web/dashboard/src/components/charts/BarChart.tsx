interface BarDatum {
  label: string;
  value: number;
}

const PLOT_HEIGHT = 160;

export function BarChart({
  data,
  emptyMessage = "Aucune donnée.",
}: {
  data: BarDatum[];
  emptyMessage?: string;
}) {
  if (data.length === 0) {
    return <p className="hint chart-empty">{emptyMessage}</p>;
  }

  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="bar-chart">
      <div className="bar-chart-plot" style={{ height: PLOT_HEIGHT }}>
        {[0, 25, 50, 75].map((pct) => (
          <div key={pct} className="bar-chart-gridline" style={{ top: `${pct}%` }} />
        ))}
        <div className="bar-chart-bars">
          {data.map((d) => (
            <div key={d.label} className="bar-chart-col" title={`${d.label} : ${d.value}`}>
              <span className="bar-chart-value">{d.value}</span>
              <div
                className="bar-chart-bar"
                style={{ height: `${(d.value / max) * 100}%` }}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="bar-chart-labels">
        {data.map((d) => (
          <span key={d.label} className="bar-chart-label" title={d.label}>
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}
