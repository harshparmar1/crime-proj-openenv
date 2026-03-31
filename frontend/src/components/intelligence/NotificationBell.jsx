import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { apiGet, apiPost } from "../../lib/api";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  const load = async () => {
    try {
      const rows = await apiGet("/notifications/");
      setItems(rows);
    } catch {
      setItems([]);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const unread = items.filter((n) => !n.read).length;

  const mark = async (id) => {
    try {
      await apiPost(`/notifications/${id}/read`, {});
    } catch {
      /* ignore */
    }
    load();
  };

  if (!localStorage.getItem("crime_token")) return null;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((v) => !v);
          load();
        }}
        className="relative p-2 rounded-xl border border-white/10 dark:border-white/10 border-slate-300 bg-slate-200/50 dark:bg-slate-800/60"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 text-[10px] bg-rose-500 text-white rounded-full px-1">{unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-auto glass z-[600] text-sm shadow-xl">
          {items.length === 0 ? (
            <div className="p-3 text-slate-500">No notifications</div>
          ) : (
            items.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => mark(n.id)}
                className={`w-full text-left p-3 border-b border-white/10 hover:bg-white/5 ${n.read ? "opacity-60" : ""}`}
              >
                <div className="font-medium">{n.title}</div>
                <div className="text-xs opacity-80">{n.body}</div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
