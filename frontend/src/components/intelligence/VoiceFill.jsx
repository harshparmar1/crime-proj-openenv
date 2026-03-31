import { Mic } from "lucide-react";
import { apiPost } from "../../lib/api";

export function VoiceFill({ defaultState, onStructured }) {
  const start = () => {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) {
      onStructured?.({ error: "Speech recognition not supported in this browser." });
      return;
    }
    const rec = new Ctor();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = async (ev) => {
      const text = ev.results[0][0].transcript;
      try {
        const ex = await apiPost("/ai/nlp/extract", { text, default_state: defaultState });
        onStructured?.({ text, ...ex });
      } catch (err) {
        onStructured?.({ error: err.message, text });
      }
    };
    rec.onerror = () => onStructured?.({ error: "Voice capture failed." });
    rec.start();
  };

  return (
    <button
      type="button"
      onClick={start}
      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-violet-500/20 border border-violet-400/40 text-sm hover:bg-violet-500/30"
    >
      <Mic size={18} /> Voice fill
    </button>
  );
}
