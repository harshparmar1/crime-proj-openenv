import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
  Legend
} from "recharts";
import {
  Car,
  Bike,
  Truck,
  ShieldAlert,
  RotateCcw,
  LogOut,
  UploadCloud,
  Sparkles,
  Sun,
  Moon,
  Radio,
  MapPinned
} from "lucide-react";
import { CrimeMapLeaflet } from "../components/intelligence/CrimeMapLeaflet";
import { PredictionPanel } from "../components/intelligence/PredictionPanel";
import { VoiceFill } from "../components/intelligence/VoiceFill";
import { PanicFab } from "../components/intelligence/PanicFab";
import { Chatbot } from "../components/intelligence/Chatbot";
import { NotificationBell } from "../components/intelligence/NotificationBell";
import { ReportTracking } from "../components/intelligence/ReportTracking";
import { Toast } from "../components/Toast";
import { STATE_REGIONS } from "../data/stateRegions";
import { apiGet, apiPost, apiUpload } from "../lib/api";
import { useCrimeSocket } from "../hooks/useCrimeSocket";
import { useTheme } from "../context/ThemeContext";

const riskColor = { Low: "bg-emerald-500/20 text-emerald-200", Medium: "bg-amber-500/20 text-amber-200", High: "bg-red-500/20 text-red-200" };

const initialForm = {
  actorType: "Individual",
  crimeType: "Theft",
  weaponUsed: "No",
  vehicleUsed: "No",
  description: "",
  phone: "",
  vehicleSelection: "None"
};

const fieldBase =
  "w-full p-2 rounded-lg border border-slate-300 dark:border-white/10 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100";

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("crime_user") || "null");
  const { theme, toggle } = useTheme();

  const defaultState = user?.state && STATE_REGIONS[user.state] ? user.state : "Maharashtra";
  const [selectedState, setSelectedState] = useState(defaultState);
  const [region, setRegion] = useState((STATE_REGIONS[defaultState] || [""])[0]);
  const [time, setTime] = useState("08:30");
  const [ampm, setAmpm] = useState("AM");
  const [form, setForm] = useState(initialForm);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [proofFileInputKey, setProofFileInputKey] = useState(0);
  const [voiceBlob, setVoiceBlob] = useState(null);
  const [voicePreviewUrl, setVoicePreviewUrl] = useState("");
  const [lastSubmitInfo, setLastSubmitInfo] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [zones, setZones] = useState([]);
  const [toast, setToast] = useState({ message: "", type: "success" });
  const [graphInput, setGraphInput] = useState({ region: "", crime_type: "", actor_type: "" });
  const [mapBlinkId, setMapBlinkId] = useState(null);
  const [geoCoords, setGeoCoords] = useState(null);
  const [mapReload, setMapReload] = useState(0);
  const [trackingTick, setTrackingTick] = useState(0);

  const regions = useMemo(() => STATE_REGIONS[selectedState] || [], [selectedState]);

  useEffect(() => {
    if (!user) navigate("/login");
  }, [user, navigate]);

  useEffect(() => {
    if (!regions.includes(region)) setRegion(regions[0] || "");
  }, [regions, region]);

  const notify = useCallback((message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: "", type: "success" }), 3200);
  }, []);

  const onLive = useCallback(
    (msg) => {
      if (!msg || !msg.type) return;
      if (msg.type === "crime_report" || msg.type === "panic") {
        notify(msg.type === "panic" ? `?? Panic / emergency signal: ${msg.region}` : `Live alert: ${msg.crime_type} (${msg.region})`, "error");
        setMapBlinkId(msg.public_id || null);
        setMapReload((k) => k + 1);
        setTimeout(() => setMapBlinkId(null), 5000);
      }
    },
    [notify]
  );

  const { connected: wsConnected } = useCrimeSocket(onLive);

  const loadZones = async () => {
    try {
      const data = await apiGet("/zones", { state: selectedState, mode: "rl" });
      setZones(data);
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const generateGraphs = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await apiGet("/analytics", {
        state: selectedState,
        region: graphInput.region,
        crime_type: graphInput.crime_type,
        actor_type: graphInput.actor_type
      });
      setAnalytics(data);
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    loadZones();
    generateGraphs();
  }, [selectedState]);

  const resetAll = () => {
    const nextState = defaultState;
    setSelectedState(nextState);
    setRegion((STATE_REGIONS[nextState] || [""])[0]);
    setTime("08:30");
    setAmpm("AM");
    setForm(initialForm);
    setFile(null);
    setPreviewUrl("");
    setProofFileInputKey((k) => k + 1);
    setGraphInput({ region: "", crime_type: "", actor_type: "" });
    setGeoCoords(null);
    if (voicePreviewUrl) URL.revokeObjectURL(voicePreviewUrl);
    setVoiceBlob(null);
    setVoicePreviewUrl("");
    setLastSubmitInfo(null);
    notify("Dashboard reset");
  };

  const logout = () => {
    localStorage.removeItem("crime_user");
    localStorage.removeItem("crime_token");
    navigate("/login");
  };

  const onFile = async (next) => {
    setFile(next);
    if (!next) {
      setPreviewUrl("");
      return;
    }
    setPreviewUrl(URL.createObjectURL(next));
    if (next.type.startsWith("audio/")) {
      return;
    }
    if (next.type.startsWith("image/")) {
      try {
        const res = await apiUpload("/ai/analyze-image", next);
        const h = res.form_hints || {};
        setForm((p) => ({
          ...p,
          weaponUsed: h.weaponUsed || p.weaponUsed,
          vehicleUsed: h.vehicleUsed || p.vehicleUsed,
          vehicleSelection: h.vehicleSelection || p.vehicleSelection
        }));
        notify("Image analysis applied to form fields", "success");
      } catch {
        notify("Image analysis unavailable", "error");
      }
    }
  };

  const applyGps = () => {
    if (!navigator.geolocation) {
      notify("Geolocation not supported", "error");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        setGeoCoords({ lat: latitude, lng: longitude });
        try {
          const hint = await apiGet("/geo/hint", { lat: latitude, lng: longitude });
          if (hint.state) setSelectedState(hint.state);
          if (hint.region) setRegion(hint.region);
          notify("Location applied to state/region", "success");
        } catch (e) {
          notify(e.message, "error");
        }
      },
      () => notify("GPS permission denied", "error"),
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  const submitReport = async () => {
    try {
      const payload = new FormData();
      payload.append("state", selectedState);
      payload.append("region", region);
      payload.append("time", `${time} ${ampm}`);
      payload.append("crime_type", form.crimeType);
      payload.append("actor_type", form.actorType);
      payload.append("weapon", form.weaponUsed);
      payload.append("vehicle", form.vehicleUsed);
      payload.append("description", form.description);
      payload.append("phone", form.phone);
      payload.append("vehicle_selection", form.vehicleSelection);
      if (geoCoords) {
        payload.append("latitude", String(geoCoords.lat));
        payload.append("longitude", String(geoCoords.lng));
      }
      if (file) payload.append("file", file);
      if (voiceBlob) {
        const ext = voiceBlob.type.includes("webm") ? "webm" : voiceBlob.type.includes("mp4") ? "m4a" : "webm";
        payload.append("voice", voiceBlob, `voice-evidence.${ext}`);
      }

      const res = await apiPost("/report", payload, true);
      const submittedLabel = res.submitted_at
        ? new Date(res.submitted_at).toLocaleString()
        : new Date().toLocaleString();
      notify(`Submitted ${submittedLabel} ? Incident: ${time} ${ampm} ? ID ${res.report_id || ""}`, "success");
      setLastSubmitInfo({
        id: res.report_id,
        submittedAt: res.submitted_at || new Date().toISOString(),
        incidentTime: `${time} ${ampm}`
      });
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      if (voicePreviewUrl) URL.revokeObjectURL(voicePreviewUrl);
      setFile(null);
      setPreviewUrl("");
      setVoiceBlob(null);
      setVoicePreviewUrl("");
      setProofFileInputKey((k) => k + 1);
      setForm((p) => ({ ...p, description: "", phone: "" }));
      setMapReload((k) => k + 1);
      setTrackingTick((t) => t + 1);
      await Promise.all([generateGraphs(), loadZones()]);
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const role = user?.role || "citizen";

  return (
    <div className="min-h-screen text-slate-900 dark:text-slate-100 p-4 md:p-8">
      <Toast message={toast.message} type={toast.type} />
      <PanicFab onStatus={notify} />
      <Chatbot
        onAutoFill={(ctx) => {
          if (ctx.crime_type) setForm((p) => ({ ...p, crimeType: ctx.crime_type }));
          if (ctx.location) setRegion(ctx.location);
          if (ctx.time) {
            const v = String(ctx.time).toLowerCase();
            if (v.includes("night")) setAmpm("PM");
            else if (v.includes("morning")) setAmpm("AM");
          }
          if (ctx.people) setForm((p) => ({ ...p, actorType: ctx.people }));
        }}
        onUrgent={() => notify("?? This seems urgent. Please use Panic button if immediate danger.", "error")}
      />
      <div className="max-w-[1700px] mx-auto space-y-4">
        <header className="glass p-4 flex flex-wrap gap-3 justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">AI Crime Intelligence Platform</h1>
            <p className="text-slate-600 dark:text-slate-300 text-sm">
              Welcome {user?.username || "Officer"} ? State: {defaultState}{" "}
              <span className="ml-2 px-2 py-0.5 rounded-full bg-sky-500/20 text-xs capitalize">{role}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`text-xs px-2 py-1 rounded-lg flex items-center gap-1 border ${
                wsConnected ? "border-emerald-500/40 text-emerald-600 dark:text-emerald-300" : "border-slate-400/40 opacity-70"
              }`}
            >
              <Radio size={14} /> {wsConnected ? "Live" : "WS"}
            </span>
            <NotificationBell />
            <button
              type="button"
              onClick={toggle}
              className="p-2 rounded-xl border border-slate-300 dark:border-white/10 bg-slate-200/50 dark:bg-slate-800/60"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              onClick={resetAll}
              className="px-4 py-2 rounded-lg bg-amber-200/30 dark:bg-amber-200/20 text-amber-900 dark:text-amber-100 hover:opacity-90 flex items-center gap-2"
            >
              <RotateCcw size={16} /> Reset
            </button>
            <button onClick={logout} className="px-4 py-2 rounded-lg bg-red-500/20 dark:bg-red-500/30 text-red-700 dark:text-red-200 flex items-center gap-2">
              <LogOut size={16} /> Logout
            </button>
          </div>
        </header>

        <div className="grid xl:grid-cols-12 gap-4">
          <section className="xl:col-span-3 space-y-4">
            <div className="glass p-4 space-y-3">
              <h2 className="font-semibold">Live operations map</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Leaflet + heat layer + incident markers (OpenStreetMap)</p>
              <CrimeMapLeaflet selectedState={selectedState} blinkKey={mapBlinkId} refreshKey={mapReload} />
            </div>
            <PredictionPanel selectedState={selectedState} region={region} time={time} ampm={ampm} form={form} />
            <ReportTracking role={role} onNotify={notify} refreshTrigger={trackingTick} />
            <button type="button" onClick={applyGps} className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-sm">
              <MapPinned size={16} /> GPS: auto state / region
            </button>
          </section>

          <section className="xl:col-span-6 space-y-4">
            <div className="glass p-4 grid md:grid-cols-4 gap-3">
              {[
                { label: "Individual / Group", key: "actorType", opts: ["Individual", "Group"] },
                { label: "Type of Crime", key: "crimeType", opts: ["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"] },
                { label: "Weapon Used", key: "weaponUsed", opts: ["Yes", "No"] },
                { label: "Vehicle Used", key: "vehicleUsed", opts: ["Yes", "No"] }
              ].map((item) => (
                <div key={item.key} className="space-y-1">
                  <div className="text-xs text-slate-600 dark:text-slate-300">{item.label}</div>
                  <select className={fieldBase} value={form[item.key]} onChange={(e) => setForm((p) => ({ ...p, [item.key]: e.target.value }))}>
                    {item.opts.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass p-4 space-y-3">
                <h3 className="font-semibold">Proof Box</h3>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <div className="text-xs text-slate-600 dark:text-slate-300">State</div>
                    <select className={fieldBase} value={selectedState} onChange={(e) => setSelectedState(e.target.value)}>
                      {Object.keys(STATE_REGIONS).map((st) => (
                        <option key={st} value={st}>
                          {st}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-slate-600 dark:text-slate-300">Region</div>
                    <select className={fieldBase} value={region} onChange={(e) => setRegion(e.target.value)}>
                      {regions.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <div className="text-xs text-slate-600 dark:text-slate-300">Incident time</div>
                    <input type="time" className={fieldBase} value={time} onChange={(e) => setTime(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-slate-600 dark:text-slate-300">AM / PM</div>
                    <select className={fieldBase} value={ampm} onChange={(e) => setAmpm(e.target.value)}>
                      <option>AM</option>
                      <option>PM</option>
                    </select>
                  </div>
                </div>
                <textarea
                  className={`${fieldBase} min-h-24`}
                  placeholder="Describe incident"
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                />
                <div className="flex flex-wrap gap-2">
                  <label className="p-2 bg-slate-200 dark:bg-slate-800 rounded-lg flex items-center gap-2 cursor-pointer flex-1 min-w-[140px]">
                    <UploadCloud size={16} /> Upload proof
                    <input
                      key={proofFileInputKey}
                      type="file"
                      accept="image/*,video/*,audio/*"
                      className="hidden"
                      onChange={(e) => onFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  <VoiceFill
                    onVoiceRecorded={(blob) => {
                      setVoiceBlob(blob);
                      setVoicePreviewUrl((prev) => {
                        if (prev) URL.revokeObjectURL(prev);
                        return URL.createObjectURL(blob);
                      });
                      notify("Voice note recorded ? it uploads when you submit.", "success");
                    }}
                    onError={(msg) => notify(msg, "error")}
                  />
                </div>
                {voicePreviewUrl ? (
                  <div className="space-y-1">
                    <div className="text-xs text-slate-500 dark:text-slate-400">Voice note (uploads with Submit)</div>
                    <audio src={voicePreviewUrl} controls className="w-full rounded-lg border border-slate-300 dark:border-white/10" />
                    <button
                      type="button"
                      className="text-xs text-rose-600 dark:text-rose-300 hover:underline"
                      onClick={() => {
                        setVoiceBlob(null);
                        setVoicePreviewUrl((prev) => {
                          if (prev) URL.revokeObjectURL(prev);
                          return "";
                        });
                      }}
                    >
                      Remove voice note
                    </button>
                  </div>
                ) : null}
                {previewUrl &&
                  (file?.type.startsWith("video") ? (
                    <video src={previewUrl} controls className="w-full rounded-lg border border-slate-300 dark:border-white/10" />
                  ) : file?.type.startsWith("audio") ? (
                    <audio src={previewUrl} controls className="w-full rounded-lg border border-slate-300 dark:border-white/10" />
                  ) : (
                    <img src={previewUrl} alt="preview" className="w-full rounded-lg border border-slate-300 dark:border-white/10" />
                  ))}
                <input
                  className={fieldBase}
                  placeholder="Phone number"
                  value={form.phone}
                  onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
                />
                <button
                  type="button"
                  onClick={submitReport}
                  className="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-500 hover:scale-[1.01] transition font-semibold text-white"
                >
                  Submit Proof
                </button>
                {lastSubmitInfo ? (
                  <div className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 dark:bg-emerald-500/5 p-3 text-xs space-y-1 text-slate-700 dark:text-slate-200">
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Submitted at: </span>
                      {new Date(lastSubmitInfo.submittedAt).toLocaleString()}
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Incident time: </span>
                      {lastSubmitInfo.incidentTime}
                    </div>
                    <div className="font-mono text-[11px] pt-1 border-t border-emerald-400/20">
                      Report ID: {lastSubmitInfo.id}
                    </div>
                  </div>
                ) : null}
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass p-4 md:col-span-2">
                <div className="flex flex-wrap gap-2 items-center justify-between mb-2">
                  <h3 className="font-semibold">Advanced analytics</h3>
                  <Sparkles size={16} className="text-sky-500 dark:text-sky-300" />
                </div>
                <div className="grid md:grid-cols-4 gap-2 mb-3">
                  <select className={fieldBase} value={graphInput.region} onChange={(e) => setGraphInput((p) => ({ ...p, region: e.target.value }))}>
                    <option value="">All Regions</option>
                    {regions.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                  <select className={fieldBase} value={graphInput.crime_type} onChange={(e) => setGraphInput((p) => ({ ...p, crime_type: e.target.value }))}>
                    <option value="">All Crimes</option>
                    <option>Theft</option>
                    <option>Robbery</option>
                    <option>Assault</option>
                    <option>Cybercrime</option>
                    <option>Fraud</option>
                  </select>
                  <select className={fieldBase} value={graphInput.actor_type} onChange={(e) => setGraphInput((p) => ({ ...p, actor_type: e.target.value }))}>
                    <option value="">All Actors</option>
                    <option>Individual</option>
                    <option>Group</option>
                  </select>
                  <button type="button" className="p-2 rounded-lg bg-sky-500/25 hover:bg-sky-500/35" onClick={generateGraphs}>
                    Update
                  </button>
                </div>
                {analyticsLoading || !analytics ? (
                  <div className="space-y-3 animate-pulse">
                    <div className="h-40 bg-slate-200 dark:bg-slate-800 rounded-xl" />
                    <div className="grid grid-cols-2 gap-3">
                      <div className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl" />
                      <div className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl" />
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="h-52">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={analytics.crime_type || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#64748b" className="dark:stroke-[#334155]" />
                          <XAxis dataKey="name" stroke="#64748b" />
                          <YAxis stroke="#64748b" />
                          <Tooltip />
                          <Bar dataKey="value" fill="#22d3ee" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="h-44 mt-3">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={analytics.region || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
                          <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} />
                          <YAxis stroke="#64748b" />
                          <Tooltip />
                          <Bar dataKey="value" fill="#a78bfa" name="Reports" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid md:grid-cols-2 gap-3 mt-3">
                      <div className="h-40">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={analytics.actor_type || []} dataKey="value" nameKey="name" outerRadius={60}>
                              {["#34d399", "#fb7185", "#f59e0b", "#38bdf8"].map((c) => (
                                <Cell key={c} fill={c} />
                              ))}
                            </Pie>
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="h-40">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={analytics.time || []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
                            <XAxis dataKey="name" stroke="#64748b" />
                            <YAxis stroke="#64748b" />
                            <Tooltip />
                            <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={2} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    <div className="h-36 mt-3">
                      <div className="text-xs mb-1 text-slate-500 dark:text-slate-400">Peak hours heat (report counts)</div>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={analytics.peak_hours || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
                          <XAxis dataKey="name" stroke="#64748b" />
                          <YAxis stroke="#64748b" />
                          <Tooltip />
                          <Bar dataKey="value" fill="#f59e0b" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                )}
              </motion.div>
            </div>

            <div className="glass p-4">
              <div className="flex justify-between mb-3 items-center">
                <h3 className="font-semibold">RL Zone Panel</h3>
                <button type="button" onClick={loadZones} className="text-sm px-3 py-1 rounded-md bg-sky-500/20 hover:bg-sky-500/30">
                  Refresh
                </button>
              </div>
              <div className="grid md:grid-cols-3 gap-2 max-h-[300px] overflow-auto pr-1">
                {zones.map((z) => (
                  <div key={`${z.state}-${z.zone}`} className={`rounded-lg p-3 border border-slate-200 dark:border-white/10 ${riskColor[z.risk] || riskColor.Medium}`}>
                    <div className="font-semibold">{z.zone}</div>
                    <div className="text-xs opacity-90">{z.state}</div>
                    <div className="text-xs mt-1">
                      Risk: {z.risk} ? Cases: {z.crime_frequency}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="xl:col-span-3 glass p-4 space-y-3">
            <h3 className="font-semibold">Vehicle Selection</h3>
            {[
              { label: "Car", icon: <Car size={18} /> },
              { label: "Bike", icon: <Bike size={18} /> },
              { label: "Truck", icon: <Truck size={18} /> },
              { label: "None", icon: <ShieldAlert size={18} /> }
            ].map((v) => (
              <button
                key={v.label}
                type="button"
                onClick={() => setForm((p) => ({ ...p, vehicleSelection: v.label }))}
                className={`w-full p-3 rounded-lg border text-left flex items-center gap-3 transition ${
                  form.vehicleSelection === v.label
                    ? "bg-sky-500/20 border-sky-400"
                    : "bg-slate-100 dark:bg-slate-900/40 border-slate-300 dark:border-white/10 hover:bg-slate-200 dark:hover:bg-slate-800/60"
                }`}
              >
                {v.icon}
                <span>{v.label}</span>
              </button>
            ))}
            <select className={fieldBase} value={form.vehicleSelection} onChange={(e) => setForm((p) => ({ ...p, vehicleSelection: e.target.value }))}>
              <option>Car</option>
              <option>Bike</option>
              <option>Truck</option>
              <option>None</option>
            </select>
          </aside>
        </div>

        <footer className="glass p-4 flex flex-col items-center gap-2 text-sm">
          <div className="text-red-600 dark:text-red-300 font-semibold">Emergency: 100 ? Disaster: 108</div>
        </footer>
      </div>
    </div>
  );
}
