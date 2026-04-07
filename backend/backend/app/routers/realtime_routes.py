from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.security import decode_token
from ..services.ws_hub import hub

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket, token: Optional[str] = None):
    """Subscribe to real-time crime events. Pass JWT as query ?token=..."""
    if token:
        try:
            decode_token(token)
        except Exception:
            await websocket.close(code=4401)
            return
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
