"""WebSocket broadcast patch for the Auris Unified Interface v4 backend."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import WebSocket, WebSocketDisconnect

from auris_unified_interface_v4 import app


class ConnectionManager:
    """Track active WebSocket clients and broadcast JSON events."""

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            recipients = list(self._connections)
        for websocket in recipients:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


async def emit_event(event: Dict[str, Any]) -> None:
    """Broadcast ``event`` to all connected WebSocket clients."""

    if not isinstance(event, dict):
        return
    await manager.broadcast(event)


__all__ = ["emit_event", "app"]
