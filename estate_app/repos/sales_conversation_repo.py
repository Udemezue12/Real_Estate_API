from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.enums import ViewingStatus
from models.models import SaleConversation, SaleListing


class SaleConversationRepo:
    def __init__(self, db):
        self.db = db

    async def set_viewing(
        self,
        *,
        convo: SaleConversation,
        viewing_date: Optional[datetime],
        status: ViewingStatus,
        set_by: UUID | None = None,
    ) -> SaleConversation:
        try:
            if convo.viewing_date == viewing_date and convo.viewing_status == status:
                return convo
            convo.viewing_date = viewing_date
            convo.viewing_status = status
            convo.last_viewing_set_by = set_by
            self.db.add(convo)

            await self.db.commit()
            await self.db.refresh(convo)
            return convo
        except IntegrityError:
            await self.db.rollback()
            raise

    async def get_conversation_by_listing_id(
        self, buyer_id: UUID, listing_id: UUID
    ) -> SaleConversation | None:
        stmt = select(SaleConversation).where(
            SaleConversation.buyer_id == buyer_id,
            SaleConversation.listing_id == listing_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, buyer_id: UUID, listing: SaleListing):
        stmt = select(SaleConversation).where(
            SaleConversation.buyer_id == buyer_id,
            SaleConversation.listing_id == listing.id,
        )
        result = await self.db.execute(stmt)
        convo = result.scalars().one_or_none()

        if convo:
            return convo

        convo = SaleConversation(
            buyer_id=buyer_id,
            listing_id=listing.id,
            seller_id=listing.listed_by_id,
        )
        self.db.add(convo)

        try:
            await self.db.commit()
            await self.db.refresh(convo)
            return convo
        except IntegrityError:
            await self.db.rollback()
            result = await self.db.execute(stmt)
            return result.scalars().one()

    async def get_conversation_by_id(
        self, conversation_id: UUID
    ) -> SaleConversation | None:
        stmt = select(SaleConversation).where(
            SaleConversation.id == conversation_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_conversations_for_user(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> list[SaleConversation]:
        stmt = (
            select(SaleConversation)
            .where(
                (SaleConversation.buyer_id == user_id)
                | (SaleConversation.seller_id == user_id)
            )
            .order_by(SaleConversation.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def hard_delete_conversation(
        self,
        conversation_id: UUID,
    ):
        try:
            convo = await self.get_conversation_by_id(conversation_id)

            await self.db.delete(convo)
            await self.db.flush()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def get_pending_conversations(self) -> List[SaleConversation]:
        cutoff = datetime.utcnow() - timedelta(hours=24)

        stmt = select(SaleConversation).where(
            SaleConversation.viewing_status == ViewingStatus.PENDING,
            SaleConversation.updated_at < cutoff,
        )
        result = await self.db.execute(stmt)
        convos: List[SaleConversation] = result.scalars().all()
        return convos

    # async def update_conversation_last_message(
    #     self, conversation_id: UUID, last_message: str
    # ) -> None:
    #     try:
    #         stmt = select(SaleConversation).where(
    #             SaleConversation.id == conversation_id,
    #         )
    #         result = await self.db.execute(stmt)
    #         conversation = result.scalar_one_or_none()
    #         if conversation:
    #              = last_message
    #             await self.db.commit()
    #     except SQLAlchemyError as e:
    #         await self.db.rollback()
    #         raise e
