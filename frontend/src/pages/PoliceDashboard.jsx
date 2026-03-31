import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  FaClipboardList,
  FaExclamationTriangle,
  FaMapMarkedAlt,
  FaShieldAlt,
  FaStream,
  FaTimes,
  FaCheck,
  FaBan,
  FaSearch,
  FaSpinner
} from "react-icons/fa";
import { Toast } from "../components/Toast";
import { apiGet, apiPatch } from "../lib/api";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: FaShieldAlt },
  { id: "live", label: "Live Reports", icon: FaStream },
  { id: "assigned", label: "Assigned Cases", icon: FaClipboardList },
  { id: "map", label: "Map View", icon: FaMapMarkedAlt }
];

const statusMeta = {
  Pending: { badge: "bg-amber-500/20 text-amber-200 border-amber-400/30", dot: "bg-amber-400" },
  Investigating: { badge: "bg-sky-500/20 text-sky-200 border-sky-400/30", dot: "bg-sky-400" },
  Resolved: { badge: "bg-emerald-500/20 text-emerald-200 border-emerald-400/30", dot: "bg-emerald-400" },
  Rejected: { badge: "bg-rose-500/20 text-rose-200 border-rose-400/30", dot: "bg-rose-400" }
};

const uiToApiStatus = {
  Pending: "pending",
  Investigating: "investigating",
  Resolved: "resolved",
  // backend currently supports: pending | investigating | resolved
  Rejected: "rejected"
};

function nowClock() {
  const d = new Date();
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function chipClass(active) {
  return `px-3 py-1 rounded-full border text-xs transition ${
    active ? "bg-white/10 border-white/20 text-white" : "bg-white/5 border-white/10 text-slate-200/80 hover:bg-white/10"
  }`;
}

function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-2 text-slate-200/80">
      <FaSpinner className="animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

function EvidenceModal({ open, onClose, report }) {
  if (!open || !report) return null;
  const isVideo = report.file_content_type?.startsWith("video");
  const isImage = report.file_content_type?.startsWith("image");

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[800] bg-black/70 flex items-center justify-center p-4"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.98 }}
          className="w-full max-w-3xl rounded-2xl border border-white/10 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 shadow-2xl"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
            <div className="space-y-0.5">
              <div className="text-lg font-semibold text-white">Evidence Viewer</div>
              <div className="text-xs text-slate-300">
                Report <span className="font-mono">{report.public_id || report.id}</span> · {report.crime_type}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-slate-200"
              aria-label="Close modal"
            >
              <FaTimes />
            </button>
          </div>

          <div className="p-5 grid md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-white/10 bg-black/20 overflow-hidden min-h-[220px] flex items-center justify-center">
              {report.evidence_url ? (
                isVideo ? (
                  <video src={report.evidence_url} controls className="w-full h-full object-contain" />
                ) : isImage ? (
                  <img src={report.evidence_url} alt="Evidence" className="w-full h-full object-contain" />
                ) : (
                  <div className="text-sm text-slate-300 p-4">Evidence file attached (unsupported preview type).</div>
                )
              ) : (
                <div className="text-sm text-slate-300 p-4">No evidence URL available yet.</div>
              )}
            </div>

            <div className="space-y-3">
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs text-slate-400">Phone</div>
                <div className="text-sm text-white">{report.phone || "—"}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs text-slate-400">Location</div>
                <div className="text-sm text-white">
                  {report.region}, {report.state}
                </div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs text-slate-400">Description</div>
                <div className="text-sm text-white whitespace-pre-wrap">{report.description || "—"}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs text-slate-400">Meta</div>
                <div className="text-sm text-white">
                  {report.time} · {report.actor_type} · Weapon: {report.weapon} · Vehicle: {report.vehicle}
                </div>
              </div>
            </div>
          </div>

          <div className="px-5 py-4 border-t border-white/10 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 text-white"
            >
              Close
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default function PoliceDashboard() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("crime_user") || "null");
  const token = localStorage.getItem("crime_token");

  // Role protection
  if (!token) return <Navigate to="/login" replace />;
  if (!user || user.role !== "police") return <Navigate to="/" replace />;

  const [active, setActive] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [toast, setToast] = useState({ message: "", type: "success" });
  const notify = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: "", type: "success" }), 2800);
  };

  // Live alerts (WS-ready structure)
  const [alerts, setAlerts] = useState([
    { id: "a1", crime_type: "Robbery", location: "Mumbai", time: "08:30 PM", ts: Date.now() - 90000 },
    { id: "a2", crime_type: "Assault", location: "Pune", time: "09:05 PM", ts: Date.now() - 48000 },
    { id: "a3", crime_type: "Cybercrime", location: "Nagpur", time: "09:20 PM", ts: Date.now() - 20000 }
  ]);

  // Reports
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selectedReport, setSelectedReport] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  // WebSocket-ready placeholder (for /ws/alerts)
  // This does NOT break if backend isn't ready; it just falls back to mock.
  useEffect(() => {
    let ws;
    try {
      // prepare for future backend: /ws/alerts (or reuse /ws/live)
      ws = new WebSocket(`ws://localhost:8000/ws/alerts?token=${encodeURIComponent(token || "")}`);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.type === "alert" || msg?.type === "crime_report" || msg?.type === "panic") {
            const location = msg.region || msg.location || "Unknown";
            const crime_type = msg.crime_type || (msg.type === "panic" ? "PANIC" : "Alert");
            const next = { id: msg.public_id || `ws_${Date.now()}`, crime_type, location, time: nowClock(), ts: Date.now() };
            setAlerts((a) => [next, ...a].slice(0, 6));
            notify(`LIVE: ${crime_type} · ${location}`, "error");
          }
        } catch {
          /* ignore */
        }
      };
    } catch {
      /* ignore */
    }
    return () => {
      try {
        ws?.close();
      } catch {
        /* ignore */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const mockReports = useMemo(
    () => [
      {
        id: 1,
        public_id: "RPT-LOCAL-0001",
        crime_type: "Robbery",
        state: "Maharashtra",
        region: "Mumbai",
        time: "08:30 PM",
        status: "Pending",
        evidence_url: "/sample.jpg",
        file_content_type: "image/jpeg",
        phone: "9876543210",
        description: "Robbery near market",
        actor_type: "Group",
        weapon: "Yes",
        vehicle: "Yes"
      },
      {
        id: 2,
        public_id: "RPT-LOCAL-0002",
        crime_type: "Assault",
        state: "Maharashtra",
        region: "Pune",
        time: "07:10 PM",
        status: "Investigating",
        evidence_url: "",
        file_content_type: "",
        phone: "9123456789",
        description: "Fight reported near station",
        actor_type: "Individual",
        weapon: "No",
        vehicle: "No"
      },
      {
        id: 3,
        public_id: "RPT-LOCAL-0003",
        crime_type: "Cybercrime",
        state: "Karnataka",
        region: "Bangalore",
        time: "11:55 AM",
        status: "Resolved",
        evidence_url: "",
        file_content_type: "",
        phone: "9000000000",
        description: "Phishing complaint submitted",
        actor_type: "Individual",
        weapon: "No",
        vehicle: "No"
      }
    ],
    []
  );

  // API-ready fetch: GET /reports (if implemented). Falls back to mock.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await apiGet("/reports");
        if (!cancelled && Array.isArray(data)) {
          // normalize minimal fields expected by UI
          setReports(
            data.map((r) => ({
              ...r,
              status: r.status ? r.status[0].toUpperCase() + r.status.slice(1) : "Pending",
              crime_type: r.crime_type || r.crime || "Unknown",
              region: r.region || r.location || "Unknown",
              time: r.time || r.created_at || nowClock()
            }))
          );
        }
      } catch {
        if (!cancelled) setReports(mockReports);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mockReports]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return reports
      .filter((r) => (statusFilter === "All" ? true : r.status === statusFilter))
      .filter((r) => {
        if (!q) return true;
        return (
          String(r.public_id || r.id).toLowerCase().includes(q) ||
          String(r.crime_type || "").toLowerCase().includes(q) ||
          String(r.region || "").toLowerCase().includes(q) ||
          String(r.state || "").toLowerCase().includes(q)
        );
      });
  }, [reports, search, statusFilter]);

  const updateLocalStatus = (id, nextStatus) => {
    setReports((rs) =>
      rs.map((r) => {
        if ((r.public_id || r.id) !== id) return r;
        return { ...r, status: nextStatus };
      })
    );
  };

  const updateStatus = async (report, nextStatus) => {
    const id = report.public_id || report.id;
    updateLocalStatus(id, nextStatus);
    notify(`Status → ${nextStatus}`, "success");

    // API-ready: PUT /reports/{id}/status (we have PATCH /reports/{id}/status in backend for now).
    // If backend route isn't available, UI still works locally.
    const apiStatus = uiToApiStatus[nextStatus] || "pending";
    if (apiStatus !== "rejected") {
      try {
        await apiPatch(`/reports/${id}/status`, { status: apiStatus });
      } catch {
        notify("Server not updated (API not available yet).", "error");
      }
    }
  };

  const openEvidence = (r) => {
    setSelectedReport(r);
    setModalOpen(true);
  };

  const logout = () => {
    localStorage.removeItem("crime_user");
    localStorage.removeItem("crime_token");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 text-white">
      <Toast message={toast.message} type={toast.type} />
      <EvidenceModal open={modalOpen} onClose={() => setModalOpen(false)} report={selectedReport} />

      {/* Mobile topbar */}
      <div className="lg:hidden sticky top-0 z-[120] backdrop-blur-xl bg-black/30 border-b border-white/10">
        <div className="flex items-center justify-between p-3">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="px-3 py-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10"
          >
            Menu
          </button>
          <div className="font-semibold">Police Dashboard</div>
          <button
            type="button"
            onClick={logout}
            className="px-3 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-orange-500 hover:opacity-90"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`fixed lg:static inset-y-0 left-0 z-[300] w-72 lg:w-80 border-r border-white/10 bg-gradient-to-b from-slate-950 to-slate-900/70 backdrop-blur-xl transform transition ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          }`}
        >
          <div className="p-5 border-b border-white/10 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-300">Unit</div>
              <div className="text-lg font-bold">Crime Intelligence</div>
              <div className="text-xs text-slate-400 mt-1">
                Officer: <span className="text-slate-200">{user?.username}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10"
              aria-label="Close sidebar"
            >
              <FaTimes />
            </button>
          </div>

          <nav className="p-3 space-y-1">
            {navItems.map((it) => {
              const Icon = it.icon;
              const isActive = active === it.id;
              return (
                <button
                  key={it.id}
                  type="button"
                  onClick={() => {
                    setActive(it.id);
                    setSidebarOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition ${
                    isActive
                      ? "bg-gradient-to-r from-sky-500/25 to-indigo-500/25 border-sky-400/30 shadow-glow"
                      : "bg-white/5 border-white/10 hover:bg-white/10"
                  }`}
                >
                  <Icon className={`${isActive ? "text-sky-300" : "text-slate-300"}`} />
                  <span className="text-sm font-medium">{it.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="p-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs text-slate-400">Status</div>
              <div className="mt-1 flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="text-sm text-slate-200">On duty</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-2">
                API ready for: <span className="text-slate-200">GET /reports</span>,{" "}
                <span className="text-slate-200">PUT/PATCH /reports/{`{id}`}/status</span>,{" "}
                <span className="text-slate-200">WS /ws/alerts</span>
              </p>
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 min-w-0 lg:ml-0">
          <div className="hidden lg:flex items-center justify-between p-6 border-b border-white/10">
            <div>
              <div className="text-xs text-slate-400">Police Operations</div>
              <h1 className="text-2xl font-bold">Police Dashboard</h1>
            </div>
            <button
              type="button"
              onClick={logout}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-orange-500 hover:opacity-90 shadow-lg"
            >
              Logout
            </button>
          </div>

          <div className="p-4 md:p-6 space-y-6">
            {/* Live alerts + Map placeholder */}
            <div className="grid lg:grid-cols-12 gap-4">
              <section className="lg:col-span-7 rounded-2xl border border-white/10 bg-white/5 shadow-xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <FaExclamationTriangle className="text-rose-300" />
                    <h2 className="font-semibold">Live Alerts</h2>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setAlerts((a) => [
                        { id: `m_${Date.now()}`, crime_type: "Robbery", location: "Mumbai", time: nowClock(), ts: Date.now() },
                        ...a
                      ].slice(0, 6))
                    }
                    className="text-xs px-3 py-1 rounded-lg border border-rose-400/30 bg-rose-500/10 hover:bg-rose-500/20"
                  >
                    + Mock alert
                  </button>
                </div>
                <div className="p-4 grid sm:grid-cols-2 gap-3">
                  {alerts.slice(0, 6).map((a) => (
                    <motion.div
                      key={a.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-2xl border border-rose-400/25 bg-gradient-to-br from-rose-600/15 to-orange-500/10 p-4 shadow-lg"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-semibold">{a.crime_type}</div>
                          <div className="text-xs text-slate-300">{a.location}</div>
                        </div>
                        <span className="text-[11px] text-slate-300">{a.time}</span>
                      </div>
                      <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-300">
                        <span className="h-2 w-2 rounded-full bg-rose-400 animate-pulse" />
                        Incoming · priority high
                      </div>
                    </motion.div>
                  ))}
                </div>
              </section>

              <section className="lg:col-span-5 rounded-2xl border border-white/10 bg-white/5 shadow-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-white/10">
                  <h2 className="font-semibold">Map View</h2>
                  <p className="text-xs text-slate-400 mt-1">Placeholder ready for Leaflet/Mapbox integration.</p>
                </div>
                <div className="p-4">
                  <div className="h-[260px] rounded-2xl border border-dashed border-white/20 bg-gradient-to-br from-sky-500/10 to-indigo-500/10 flex items-center justify-center">
                    <div className="text-center">
                      <FaMapMarkedAlt className="mx-auto text-sky-300 text-3xl" />
                      <div className="mt-2 text-sm text-slate-200">Map placeholder</div>
                      <div className="text-xs text-slate-400">Integrate clusters, heatmap, popups</div>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {/* Reports management */}
            <section className="rounded-2xl border border-white/10 bg-white/5 shadow-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-white/10 flex flex-wrap gap-3 items-center justify-between">
                <div>
                  <h2 className="font-semibold">Reports Management</h2>
                  <p className="text-xs text-slate-400">Accept / Reject / Investigate / Resolve · instant UI state updates</p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300 text-sm" />
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search ID / crime / location…"
                      className="pl-9 pr-3 py-2 rounded-xl border border-white/10 bg-black/20 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-400/30"
                    />
                  </div>
                  <div className="flex gap-1 rounded-xl border border-white/10 bg-black/20 p-1">
                    {["All", "Pending", "Investigating", "Resolved", "Rejected"].map((s) => (
                      <button key={s} type="button" onClick={() => setStatusFilter(s)} className={chipClass(statusFilter === s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="p-4">
                {loading ? (
                  <Spinner label="Loading reports…" />
                ) : filtered.length === 0 ? (
                  <div className="text-sm text-slate-300">No matching reports.</div>
                ) : (
                  <div className="overflow-auto rounded-xl border border-white/10">
                    <table className="min-w-full text-sm">
                      <thead className="bg-black/30 text-slate-200">
                        <tr>
                          <th className="text-left px-4 py-3 font-medium">Report ID</th>
                          <th className="text-left px-4 py-3 font-medium">Crime Type</th>
                          <th className="text-left px-4 py-3 font-medium">Location</th>
                          <th className="text-left px-4 py-3 font-medium">Time</th>
                          <th className="text-left px-4 py-3 font-medium">Status</th>
                          <th className="text-left px-4 py-3 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/10">
                        {filtered.map((r) => {
                          const id = r.public_id || r.id;
                          const meta = statusMeta[r.status] || statusMeta.Pending;
                          return (
                            <tr key={id} className="hover:bg-white/5 transition">
                              <td className="px-4 py-3 font-mono text-xs text-slate-200">{id}</td>
                              <td className="px-4 py-3 text-slate-100">{r.crime_type}</td>
                              <td className="px-4 py-3 text-slate-200">
                                {r.region}
                                {r.state ? <span className="text-slate-400">, {r.state}</span> : null}
                              </td>
                              <td className="px-4 py-3 text-slate-200">{r.time}</td>
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
                                    onClick={() => updateStatus(r, "Investigating")}
                                    className="px-3 py-1 rounded-lg bg-sky-500/15 border border-sky-400/30 hover:bg-sky-500/25 text-xs inline-flex items-center gap-2"
                                  >
                                    <FaCheck /> Accept
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => updateStatus(r, "Rejected")}
                                    className="px-3 py-1 rounded-lg bg-rose-500/15 border border-rose-400/30 hover:bg-rose-500/25 text-xs inline-flex items-center gap-2"
                                  >
                                    <FaBan /> Reject
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => updateStatus(r, "Investigating")}
                                    className="px-3 py-1 rounded-lg bg-indigo-500/15 border border-indigo-400/30 hover:bg-indigo-500/25 text-xs"
                                  >
                                    Mark Investigating
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => updateStatus(r, "Resolved")}
                                    className="px-3 py-1 rounded-lg bg-emerald-500/15 border border-emerald-400/30 hover:bg-emerald-500/25 text-xs"
                                  >
                                    Mark Resolved
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => openEvidence(r)}
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

            {/* Assigned cases section (placeholder but functional with filter) */}
            <section className="rounded-2xl border border-white/10 bg-white/5 shadow-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-white/10">
                <h2 className="font-semibold">Assigned Cases</h2>
                <p className="text-xs text-slate-400 mt-1">Ready for future assignment logic (by station / officer id).</p>
              </div>
              <div className="p-4 text-sm text-slate-200/90">
                Current view uses the same reports list. Add assignment fields server-side (e.g. `assigned_to`, `station_id`) and filter here.
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

