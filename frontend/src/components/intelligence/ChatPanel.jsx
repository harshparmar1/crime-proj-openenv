import { useState } from "react";
import { MessageCircle, Send } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiPost } from "../../lib/api";

export function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);

  const send = async () => {
    const q = input.trim();
    if (!q) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    try {
      const res = await apiPost("/chat/", { message: q });
      setMessages((m) => [...m, { role: "bot", text: res.answer, meta: res.source }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: e.message, meta: "error" }]);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 left-6 z-[500] p-4 rounded-full bg-indigo-600 text-white shadow-xl border border-indigo-300/50"
      >
        <MessageCircle size={22} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            className="fixed bottom-24 left-6 z-[500] w-[min(100vw-3rem,380px)] glass p-3 flex flex-col gap-2 max-h-[420px]"
          >
            <div className="text-sm font-semibold">Crime intelligence chat</div>
            <div className="flex-1 overflow-auto space-y-2 text-sm max-h-64 pr-1">
              {messages.length === 0 && (
                <p className="text-slate-500 dark:text-slate-400 text-xs">Try: “Safest area in Mumbai?”</p>
              )}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-2 py-1 ${
                    m.role === "user"
                      ? "bg-sky-500/20 ml-6 text-right"
                      : "bg-slate-200/80 dark:bg-slate-800/80 mr-6"
                  }`}
                >
                  {m.text}
                  {m.meta && <div className="text-[10px] opacity-60 mt-0.5">via {m.meta}</div>}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                className="flex-1 p-2 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-white/10 text-sm"
                value={input}
                placeholder="Ask about crime patterns…"
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
              />
              <button type="button" onClick={send} className="p-2 rounded-lg bg-sky-500 text-white">
                <Send size={18} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
