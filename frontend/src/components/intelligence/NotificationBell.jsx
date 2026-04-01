import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Bell } from "lucide-react";
import { apiGet, apiPost } from "../../lib/api";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const btnRef = useRef(null);
  const [panelPos, setPanelPos] = useState({ top: 0, right: 0 });

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

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return;
    const update = () => {
      const el = btnRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      setPanelPos({
        top: rect.bottom + 8,
        right: Math.max(8, window.innerWidth - rect.right)
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

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

  const panel =
    open &&
    typeof document !== "undefined" &&
    createPortal(
      <>
        <button
          type="button"
          className="fixed inset-0 z-[10000] cursor-default bg-black/30"
          aria-label="Close notifications"
          onClick={() => setOpen(false)}
        />
        <div
          role="dialog"
          aria-modal="true"
          className="fixed z-[10001] w-80 max-h-[min(24rem,70vh)] overflow-auto text-sm shadow-2xl rounded-xl border border-slate-200/70 bg-white/90 text-slate-900 dark:border-white/15 dark:bg-slate-900/80 dark:text-slate-100 backdrop-blur-xl"
          style={{ top: panelPos.top, right: panelPos.right }}
        >
          {items.length === 0 ? (
            <div className="p-3 text-slate-600 dark:text-slate-400">No notifications</div>
          ) : (
            items.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => mark(n.id)}
                className={`w-full text-left p-3 border-b border-slate-200/60 dark:border-white/10 last:border-b-0 hover:bg-slate-100/70 dark:hover:bg-white/10 transition-colors ${n.read ? "opacity-70" : "bg-amber-500/10"}`}
              >
                <div className="font-medium text-slate-900 dark:text-slate-100">{n.title}</div>
                <div className="text-xs text-slate-600 dark:text-slate-300">{n.body}</div>
              </button>
            ))
          )}
        </div>
      </>,
      document.body
    );

  return (
    <div className="relative">
      <button
        ref={btnRef}
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
      {panel}
    </div>
  );
}
