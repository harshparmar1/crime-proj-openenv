from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import WebSocket


class ConnectionHub:
    """Native WebSocket fan-out for real-time crime intelligence."""

    def __init__(self) -> None:
        self._clients: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._clients:
                self._clients.remove(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            snapshot = list(self._clients)
        stale: List[WebSocket] = []
        for ws in snapshot:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    if ws in self._clients:
                        self._clients.remove(ws)


hub = ConnectionHub()
