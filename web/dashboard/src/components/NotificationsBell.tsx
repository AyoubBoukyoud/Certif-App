import { useEffect, useState } from "react";
import { useAuth } from "../lib/AuthContext";
import { supabase } from "../lib/supabaseClient";
import { IconBell } from "./icons";

// No `notifications` table exists yet (backlog — see
// ~/.claude/plans/harmonic-cuddling-flask.md §11 / the older plan's §7.6) —
// this type is declared locally rather than in database.types.ts, which
// only describes tables that actually exist on the live project. The bell
// renders empty until that table is built.
interface NotificationRow {
  id: string;
  title: string;
  body: string | null;
  read_at: string | null;
}

export function NotificationsBell() {
  const { profile } = useAuth();
  const [items, setItems] = useState<NotificationRow[]>([]);
  const [open, setOpen] = useState(false);

  async function refresh() {
    if (!profile) return;
    const { data, error } = await supabase
      .from("notifications")
      .select("*")
      .eq("recipient_id", profile.id)
      .order("created_at", { ascending: false })
      .limit(10);
    if (error) return;
    setItems((data as unknown as NotificationRow[]) ?? []);
  }

  useEffect(() => {
    refresh();
  }, [profile?.id]);

  const unreadCount = items.filter((n) => !n.read_at).length;

  async function markRead(id: string) {
    await supabase.from("notifications").update({ read_at: new Date().toISOString() }).eq("id", id);
    refresh();
  }

  return (
    <div className="notif-wrap">
      <button
        className="notif-bell"
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
      >
        <IconBell size={18} />
        {unreadCount > 0 && <span className="notif-count">{unreadCount}</span>}
      </button>
      {open && (
        <div className="notif-dropdown">
          <h3>Notifications</h3>
          {items.length === 0 && <p className="hint">Aucune notification.</p>}
          <ul>
            {items.map((n) => (
              <li
                key={n.id}
                className={n.read_at ? "" : "unread"}
                onClick={() => !n.read_at && markRead(n.id)}
              >
                <strong>{n.title}</strong>
                {n.body && <p>{n.body}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
