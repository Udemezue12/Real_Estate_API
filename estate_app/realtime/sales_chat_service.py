from uuid import UUID

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import SaleConversation
from realtime.connection_manager import ConnectionManager

from .message_repo import SaleEncryptedMessageRepo


class ChatService:
    def __init__(
        self,
        db: AsyncSession,
        current_user,
        manager: ConnectionManager,
    ):
        self.db = db
        self.current_user = current_user
        self.manager = manager
        self.message_repo = SaleEncryptedMessageRepo(db)


    async def on_connect(
        self,
        websocket: WebSocket,
        conversation_id: UUID,
    ):
        convo = await self._validate_conversation(conversation_id)
        await self.manager.connect(conversation_id, websocket)
        return convo

    async def on_disconnect(
        self,
        conversation_id: UUID,
        websocket: WebSocket,
    ):
        await self.manager.disconnect(conversation_id, websocket)

 
    async def on_message(
        self,
        conversation_id: UUID,
        payload: dict,
    ):
        convo = await self._validate_conversation(conversation_id)

        msg = await self._persist_message(
            convo=convo,
            ciphertext=payload["ciphertext"],
            nonce=payload["nonce"],
            sender_public_key=payload["sender_public_key"],
        )

        await self.manager.broadcast(
            conversation_id,
            self._serialize_message(msg),
        )

  
    async def _validate_conversation(
        self,
        conversation_id: UUID,
    ) -> SaleConversation:
        convo = await self.db.get(SaleConversation, conversation_id)

        if not convo:
            raise ValueError("Conversation not found")

        if self.current_user.id not in (convo.buyer_id, convo.seller_id):
            raise PermissionError("Access denied")

        return convo

    async def _persist_message(
        self,
        *,
        convo: SaleConversation,
        ciphertext: str,
        nonce: str,
        sender_public_key: str,
    ):
        sender_id = self.current_user.id
        receiver_id = (
            convo.seller_id
            if sender_id == convo.buyer_id
            else convo.buyer_id
        )

        return await self.message_repo.create(
            conversation_id=convo.id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            ciphertext=ciphertext,
            nonce=nonce,
            sender_public_key=sender_public_key,
        )

 
    def _serialize_message(self, msg) -> dict:
        return {
            "id": str(msg.id),
            "conversation_id": str(msg.conversation_id),
            "sender_id": str(msg.sender_id),
            "receiver_id": str(msg.receiver_id),
            "ciphertext": msg.ciphertext,
            "nonce": msg.nonce,
            "sender_public_key": msg.sender_public_key,
            "created_at": msg.created_at.isoformat(),
        }
