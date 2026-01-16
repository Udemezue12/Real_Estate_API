from uuid import UUID
from models.models import SaleEncryptedMessage
from sqlalchemy import select, and_, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone


class SaleEncryptedMessageRepository:
    def __init__(self, db):
        self.db = db

    async def create(
        self,
        conversation_id: UUID,
        sender_id: UUID,
        receiver_id: UUID,
        ciphertext: str,
        nonce: str,
        sender_public_key: str,
    ):
        try:
            msg = SaleEncryptedMessage(
                conversation_id=conversation_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                ciphertext=ciphertext,
                nonce=nonce,
                sender_public_key=sender_public_key,
            )
            self.db.add(msg)
            await self.db.flush()
            return msg
        except IntegrityError:
            await self.db.rollback()
            raise

    async def list_for_conversation(self, conversation_id: UUID):
        stmt = (
            select(SaleEncryptedMessage)
            .where(SaleEncryptedMessage.conversation_id == conversation_id)
            .order_by(SaleEncryptedMessage.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_for_conversation_for_user(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ):
        stmt = (
            select(SaleEncryptedMessage)
            .options(
                selectinload(SaleEncryptedMessage.sender),
                selectinload(SaleEncryptedMessage.receiver),
            )
            .where(
                SaleEncryptedMessage.conversation_id == conversation_id,
                (
                    (SaleEncryptedMessage.sender_id == user_id)
                    & (SaleEncryptedMessage.sender_deleted == False)
                )
                | (
                    (SaleEncryptedMessage.receiver_id == user_id)
                    & (SaleEncryptedMessage.receiver_deleted == False)
                ),
            )
            .order_by(SaleEncryptedMessage.created_at)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_for_conversation_for_user_cursor(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = 20,
        before: datetime | None = None,
    ):
        conditions = [
            SaleEncryptedMessage.conversation_id == conversation_id,
            or_(
                and_(
                    SaleEncryptedMessage.sender_id == user_id,
                    SaleEncryptedMessage.sender_deleted.is_(False),
                ),
                and_(
                    SaleEncryptedMessage.receiver_id == user_id,
                    SaleEncryptedMessage.receiver_deleted.is_(False),
                ),
            ),
        ]

        if before:
            conditions.append(SaleEncryptedMessage.created_at < before)

        stmt = (
            select(SaleEncryptedMessage)
            .where(*conditions)
            .order_by(SaleEncryptedMessage.created_at.desc())
            .limit(limit + 1)
        )

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        has_more = len(messages) > limit
        items = messages[:limit]

        next_cursor = items[-1].created_at if has_more else None

        return items, next_cursor

    async def get_encrypted_message_id(
        self, message_id: UUID
    ) -> SaleEncryptedMessage | None:
        stmt = select(SaleEncryptedMessage).where(SaleEncryptedMessage.id == message_id)
        result = await self.db.execute(stmt)
        return result.scalars().one_or_none()

    async def soft_delete_for_user(self, message_id: UUID, user_id: UUID):
        try:
            msg = await self.get_encrypted_message_id(message_id)

            if not msg:
                return None

            if msg.sender_id == user_id:
                msg.sender_deleted = True
            elif msg.receiver_id == user_id:
                msg.receiver_deleted = True
            else:
                raise PermissionError("Not allowed")

            await self.db.flush()
            return msg
        except IntegrityError:
            await self.db.rollback()
            raise

    async def mark_conversation_as_read(self, conversation_id: UUID, user_id: UUID):
        try:
            stmt = (
                update(SaleEncryptedMessage)
                .where(
                    SaleEncryptedMessage.conversation_id == conversation_id,
                    SaleEncryptedMessage.receiver_id == user_id,
                    SaleEncryptedMessage.is_read.is_(False),
                )
                .values(
                    is_read=True,
                    read_at=datetime.now(timezone.utc),
                )
            )
            await self.db.execute(stmt)
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise
