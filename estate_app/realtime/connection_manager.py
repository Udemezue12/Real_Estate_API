from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, list[WebSocket]] = {}

    async def connect(self, conversation_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(conversation_id, []).append(websocket)

    async def disconnect(self, conversation_id: UUID, websocket: WebSocket):
        connections = self.active_connections.get(conversation_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(conversation_id, None)

    async def broadcast(self, conversation_id: UUID, payload: dict):
        for ws in self.active_connections.get(conversation_id, []):
            await ws.send_json(payload)
