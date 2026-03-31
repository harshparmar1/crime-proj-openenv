import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Clock, MapPin } from "lucide-react";
import { apiGet, apiPost } from "../../lib/api";

export function PredictionPanel({ selectedState, region, time, ampm, form }) {
  const [zones, setZones] = useState([]);
  const [live, setLive] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        const z = await apiGet("/predict/zones", { state: selectedState });
        if (!c) setZones(z.high_risk || []);
      } catch {
        if (!c) setZones([]);
      }
    })();
    return () => {
      c = true;
    };
  }, [selectedState]);

  const runPredict = async () => {
    setLoading(true);
    try {
      const p = await apiPost("/predict", {
        state: selectedState,
        region,
        time: `${time} ${ampm}`,
        crime_type: form.crimeType,
        actor_type: form.actorType
      });
      setLive(p);
    } catch {
      setLive(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <AlertTriangle className="text-amber-300" size={18} /> AI Prediction
        </h3>
        <button type="button" onClick={runPredict} className="text-xs px-3 py-1 rounded-lg bg-sky-500/25 hover:bg-sky-500/35 dark:bg-sky-500/25">
          {loading ? "…" : "Run"}
        </button>
      </div>
      <div className="text-xs text-slate-600 dark:text-slate-300 flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-200/80 dark:bg-slate-800 border border-slate-300/60 dark:border-white/10">
          <MapPin size={12} /> High-risk zones
        </span>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-200/80 dark:bg-slate-800 border border-slate-300/60 dark:border-white/10">
          <Clock size={12} /> Time-aware
        </span>
      </div>
      <ul className="space-y-2 max-h-40 overflow-auto text-sm">
        {zones.map((z) => (
          <li
            key={z.region}
            className={`flex justify-between rounded-lg px-2 py-1 border ${
              z.risk_level === "High"
                ? "border-rose-500/50 bg-rose-500/10"
                : z.risk_level === "Medium"
                  ? "border-amber-500/40 bg-amber-500/10"
                  : "border-white/10 bg-slate-900/30 dark:bg-slate-900/30 bg-slate-100/80"
            }`}
          >
            <span>{z.region}</span>
            <span className="text-xs opacity-90">
              ⚠️ {z.risk_level} · {z.reports} cases · {(z.confidence * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
      {live && (
        <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 p-2 text-sm space-y-1">
          <div className="font-medium">Current selection risk: {live.risk_level}</div>
          <div className="text-xs opacity-80">Confidence: {live.confidence}</div>
          <div className="text-[11px] opacity-70">Model: {live.model}</div>
        </div>
      )}
    </motion.div>
  );
}
