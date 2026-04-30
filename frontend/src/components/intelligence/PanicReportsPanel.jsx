import { useEffect, useMemo, useState } from "react";
import { FaBan, FaCheck } from "react-icons/fa";
import { API_BASE, authHeaders } from "../../lib/api";

const statusMeta = {
  Pending: { badge: "bg-amber-500/20 text-amber-200 border-amber-400/30", dot: "bg-amber-400" },
  Investigating: { badge: "bg-sky-500/20 text-sky-200 border-sky-400/30", dot: "bg-sky-400" },
  Resolved: { badge: "bg-emerald-500/20 text-emerald-200 border-emerald-400/30", dot: "bg-emerald-400" },
  Rejected: { badge: "bg-rose-500/20 text-rose-200 border-rose-400/30", dot: "bg-rose-400" }
};

export function PanicReportsPanel({ reports, onViewEvidence, onUpdateStatus }) {
  const panicReports = useMemo(() => (reports || []).filter((r) => r.is_panic), [reports]);
  const [photoUrls, setPhotoUrls] = useState({});

  useEffect(() => {
    let cancelled = false;
    const objectUrls = [];

    (async () => {
      const rows = await Promise.all(
        panicReports.map(async (r) => {
          const id = r.public_id || r.id;
          if (!id || !r.has_file) return [id, null];
          try {
            const res = await fetch(`${API_BASE}/reports/${encodeURIComponent(id)}/file`, {
              headers: { ...authHeaders() },
            });
            if (!res.ok) return [id, null];
            const blob = await res.blob();
            if (!blob.type.startsWith("image")) return [id, null];
            const url = URL.createObjectURL(blob);
            objectUrls.push(url);
            return [id, url];
          } catch {
            return [id, null];
          }
        })
      );

      if (cancelled) {
        objectUrls.forEach((u) => URL.revokeObjectURL(u));
        return;
      }

      const next = {};
      rows.forEach(([id, url]) => {
        if (id && url) next[id] = url;
      });
      setPhotoUrls(next);
    })();

    return () => {
      cancelled = true;
      objectUrls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [panicReports]);

  return (
    <section className="rounded-2xl border border-rose-400/30 bg-rose-500/5 shadow-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-rose-400/20 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-rose-200">Panic Reports</h2>
          <p className="text-xs text-rose-200/70">Critical alerts from panic button triggers</p>
        </div>
        <span className="text-xs px-2 py-1 rounded-full bg-rose-500/20 border border-rose-400/40 text-rose-100">
          {panicReports.length} active
        </span>
      </div>

      <div className="p-4">
        {panicReports.length === 0 ? (
          <div className="text-sm text-rose-200/70">No panic alerts yet.</div>
        ) : (
          <div className="overflow-auto rounded-xl border border-rose-400/20">
            <table className="min-w-full text-sm">
              <thead className="bg-rose-500/10 text-rose-100">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Report ID</th>
                  <th className="text-left px-4 py-3 font-medium">Location</th>
                  <th className="text-left px-4 py-3 font-medium">Time</th>
                  <th className="text-left px-4 py-3 font-medium">Photo</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rose-400/20">
                {panicReports.map((r) => {
                  const id = r.public_id || r.id;
                  const meta = statusMeta[r.status] || statusMeta.Pending;
                  const hasCoords = r.latitude !== null && r.latitude !== undefined && r.longitude !== null && r.longitude !== undefined;
                  const locationLabel = r.current_location || (hasCoords
                    ? `${Number(r.latitude).toFixed(5)}, ${Number(r.longitude).toFixed(5)}`
                    : `${r.region}${r.state ? `, ${r.state}` : ""}`);
                  return (
                    <tr key={id} className="hover:bg-rose-500/10 transition">
                      <td className="px-4 py-3 font-mono text-xs text-rose-100">{id}</td>
                      <td className="px-4 py-3 text-rose-100">
                        {locationLabel}
                      </td>
                      <td className="px-4 py-3 text-rose-100">{r.time}</td>
                      <td className="px-4 py-3">
                        {photoUrls[id] ? (
                          <button
                            type="button"
                            onClick={() => onViewEvidence?.(r)}
                            className="rounded-lg border border-rose-300/30 overflow-hidden hover:opacity-90 transition"
                            title="Open emergency photo"
                          >
                            <img
                              src={photoUrls[id]}
                              alt="Emergency snapshot"
                              className="w-20 h-14 object-cover"
                            />
                          </button>
                        ) : (
                          <span className="text-xs text-rose-200/70">No photo</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${meta.badge}`}>
                          <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => onUpdateStatus?.(r, "Investigating")}
                            className="px-3 py-1 rounded-lg bg-sky-500/15 border border-sky-400/30 hover:bg-sky-500/25 text-xs inline-flex items-center gap-2"
                          >
                            <FaCheck /> Accept
                          </button>
                          <button
                            type="button"
                            onClick={() => onUpdateStatus?.(r, "Rejected")}
                            className="px-3 py-1 rounded-lg bg-rose-500/15 border border-rose-400/30 hover:bg-rose-500/25 text-xs inline-flex items-center gap-2"
                          >
                            <FaBan /> Reject
                          </button>
                          <button
                            type="button"
                            onClick={() => onViewEvidence?.(r)}
                            className="px-3 py-1 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-xs"
                          >
                            View Evidence
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
