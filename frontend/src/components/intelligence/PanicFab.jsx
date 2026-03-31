import { useState } from "react";
import { AlertOctagon } from "lucide-react";
import { API_BASE, authHeaders } from "../../lib/api";

async function captureSnapshotBlob() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  const video = document.createElement("video");
  video.playsInline = true;
  video.srcObject = stream;
  await video.play();
  await new Promise((r) => setTimeout(r, 400));
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  stream.getTracks().forEach((t) => t.stop());
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
}

export function PanicFab({ onStatus }) {
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!localStorage.getItem("crime_token")) {
      onStatus?.("Login required for panic alerts.", "error");
      return;
    }
    setBusy(true);
    try {
      const pos = await new Promise((res, rej) => {
        navigator.geolocation.getCurrentPosition(res, rej, { enableHighAccuracy: true, timeout: 12000 });
      });
      let blob = null;
      try {
        blob = await captureSnapshotBlob();
      } catch {
        /* camera denied — still send location */
      }
      const fd = new FormData();
      fd.append("latitude", String(pos.coords.latitude));
      fd.append("longitude", String(pos.coords.longitude));
      if (blob) fd.append("snapshot", blob, "panic.jpg");

      const res = await fetch(`${API_BASE}/panic/`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: fd
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Panic send failed");
      onStatus?.(`Panic sent. Report ${data.report_id}`, "success");
    } catch (e) {
      onStatus?.(e.message || "Panic failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      disabled={busy}
      onClick={run}
      className="fixed bottom-6 right-6 z-[500] flex items-center gap-2 px-5 py-4 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-bold shadow-2xl shadow-rose-900/50 border border-rose-400/60 disabled:opacity-60 animate-pulse"
    >
      <AlertOctagon size={22} />
      {busy ? "Sending…" : "PANIC"}
    </button>
  );
}
