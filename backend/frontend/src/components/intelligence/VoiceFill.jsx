import { useRef, useState } from "react";
import { Mic, Square } from "lucide-react";

export function VoiceFill({ onVoiceRecorded, onError }) {
  const [recording, setRecording] = useState(false);
  const recRef = useRef(null);
  const streamRef = useRef(null);

  const startRecording = async () => {
    if (recording) {
      try {
        recRef.current?.stop();
      } catch {
        /* ignore */
      }
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const mr = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      const chunks = [];
      mr.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      mr.onstop = () => {
        const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
        onVoiceRecorded?.(blob);
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      };
      mr.start();
      recRef.current = mr;
      setRecording(true);
    } catch {
      onError?.("Microphone access denied or unavailable.");
    }
  };

  return (
    <button
      type="button"
      onClick={startRecording}
      className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
        recording
          ? "bg-rose-500/25 border-rose-400/50 text-rose-100 animate-pulse"
          : "bg-emerald-500/15 border-emerald-400/40 hover:bg-emerald-500/25"
      }`}
      title={recording ? "Stop and save voice note" : "Record voice evidence (saved with Submit)"}
    >
      {recording ? <Square size={16} /> : <Mic size={18} />}
      {recording ? "Stop recording" : "Voice note"}
    </button>
  );
}
