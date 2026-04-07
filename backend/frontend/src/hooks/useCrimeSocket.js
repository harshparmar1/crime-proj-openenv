import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "../lib/api";

export function useCrimeSocket(onEvent) {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    const token = localStorage.getItem("crime_token") || "";
    const url = `${WS_BASE}/ws/live${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    let ws;
    try {
      ws = new WebSocket(url);
    } catch {
      return undefined;
    }
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        onEventRef.current?.(data);
      } catch {
        /* ignore */
      }
    };
    return () => {
      try {
        ws.close();
      } catch {
        /* ignore */
      }
    };
  }, []);

  return { connected };
}
