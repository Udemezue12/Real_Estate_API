from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.models import SaleEncryptedMessage


class SaleEncryptedMessageRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        conversation_id: UUID,
        sender_id: UUID,
        receiver_id: UUID,
        ciphertext: str,
        nonce: str,
        sender_public_key: str,
    ) -> SaleEncryptedMessage:
        msg = SaleEncryptedMessage(
            conversation_id=conversation_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            ciphertext=ciphertext,
            nonce=nonce,
            sender_public_key=sender_public_key,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg
