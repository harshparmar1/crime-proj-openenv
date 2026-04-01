import { createPortal } from "react-dom";
import { CheckCircle2, XCircle } from "lucide-react";

export function Toast({ message, type = "success" }) {
  if (!message) return null;
  const isSuccess = type === "success";
  const node = (
    <div
      className={`pointer-events-auto fixed right-4 top-4 z-[10060] max-w-[min(100vw-2rem,28rem)] px-4 py-3 rounded-xl shadow-glow border ${isSuccess ? "bg-emerald-500/20 border-emerald-400/30 text-emerald-200" : "bg-red-500/20 border-red-400/30 text-red-200"}`}
    >
      <div className="flex items-center gap-2">
        {isSuccess ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
        <span>{message}</span>
      </div>
    </div>
  );
  if (typeof document === "undefined") return null;
  return createPortal(node, document.body);
}
