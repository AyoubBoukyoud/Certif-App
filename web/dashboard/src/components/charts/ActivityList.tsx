interface ActivityItem {
  id: number;
  event: string;
  created_at: string;
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ActivityList({ items }: { items: ActivityItem[] }) {
  if (items.length === 0) {
    return <p className="hint">Aucune activité récente.</p>;
  }
  return (
    <ul className="activity-list">
      {items.map((item) => (
        <li key={item.id}>
          <span className="activity-event">{item.event}</span>
          <span className="activity-time">{formatWhen(item.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}
