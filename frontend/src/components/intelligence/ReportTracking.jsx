import { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import { apiGet, apiPatch } from "../../lib/api";

const statusColors = {
  pending: "bg-amber-500/20 text-amber-200",
  investigating: "bg-sky-500/20 text-sky-200",
  resolved: "bg-emerald-500/20 text-emerald-200"
};

export function ReportTracking({ role, onNotify }) {
  const [rows, setRows] = useState([]);

  const load = async () => {
    try {
      const data = await apiGet("/reports/tracking");
      setRows(data);
    } catch {
      setRows([]);
    }
  };

  useEffect(() => {
    if (localStorage.getItem("crime_token")) load();
  }, []);

  const updateStatus = async (id, status) => {
    try {
      await apiPatch(`/reports/${id}/status`, { status });
      onNotify?.(`Status → ${status}`, "success");
      load();
    } catch (e) {
      onNotify?.(e.message, "error");
    }
  };

  if (!localStorage.getItem("crime_token")) return null;

  return (
    <div className="glass p-4 space-y-2">
      <div className="font-semibold flex items-center gap-2">
        <ClipboardList size={18} /> My reports
      </div>
      <div className="max-h-48 overflow-auto space-y-2 text-xs">
        {rows.length === 0 && <div className="opacity-60">No tracked reports yet. Submit with login to attach ID.</div>}
        {rows.map((r) => (
          <div key={r.report_id} className="rounded-lg border border-white/10 p-2 space-y-1">
            <div className="flex justify-between gap-2">
              <span className="font-mono truncate">{r.report_id}</span>
              <span className={`px-2 py-0.5 rounded ${statusColors[r.status] || ""}`}>{r.status}</span>
            </div>
            <div>
              {r.crime_type} · {r.region}
            </div>
            {(role === "police" || role === "admin") && (
              <div className="flex flex-wrap gap-1 pt-1">
                {["pending", "investigating", "resolved"].map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="px-2 py-0.5 rounded bg-slate-700/60 hover:bg-slate-600 text-[10px]"
                    onClick={() => updateStatus(r.report_id, s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
