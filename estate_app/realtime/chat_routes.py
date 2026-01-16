from uuid import UUID

from core.get_current_user import get_current_user_ws
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency_ws
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from realtime.connection_manager import ConnectionManager

from .sales_chat_service import ChatService

router = APIRouter(tags=["Encrypted Chat Realtime"])
manager = ConnectionManager()


@router.websocket("/ws/sale/chat/{conversation_id}", dependencies=[rate_limit])
@safe_handler
async def sale_chat_endpoint(
    websocket: WebSocket,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_async),
    _: None = Depends(validate_csrf_dependency_ws),
):
    current_user = await get_current_user_ws(websocket, db)
    chat_service = ChatService(db, current_user, manager)

    try:
        await chat_service.on_connect(websocket, conversation_id)
        while True:
            data = await websocket.receive_json()
            await chat_service.on_message(conversation_id, data)
    except WebSocketDisconnect:
        await chat_service.on_disconnect(conversation_id, websocket)
