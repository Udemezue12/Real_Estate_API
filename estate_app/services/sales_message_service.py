from datetime import datetime, timezone
from uuid import UUID

from core.breaker import CircuitBreaker
from core.cache import Cache
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from fastapi import HTTPException
from models.enums import ViewingStatus
from repos.sale_listing_repo import SaleListingRepo
from repos.sales_conversation_repo import SaleConversationRepo
from repos.sales_encrypted_message import SaleEncryptedMessageRepository
from repos.sales_log_history_repo import SaleViewHistoryRepo
from schemas.schema import (
    CursorPage,
    SaleConversationOut,
    EncryptedMessageOut,
    MessageCursorOut,
    MessageOut,
)


class SalesMessagingService:
    def __init__(self, db):
        self.db = db
        self.cache: Cache = Cache()
        self.logs: SaleViewHistoryRepo = SaleViewHistoryRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.breaker: CircuitBreaker = CircuitBreaker()
        self.convos: SaleConversationRepo = SaleConversationRepo(db)
        self.messages: SaleEncryptedMessageRepository = SaleEncryptedMessageRepository(
            db
        )
        self.mapper: ORMMapper = ORMMapper()
        self.listings: SaleListingRepo = SaleListingRepo(db)

    async def schedule_viewing(
        self,
        *,
        convo_id: UUID,
        viewing_date: datetime,
        current_user,
    ):
        async def handler():
            convo = await self.convos.get_conversation_by_id(convo_id)

            if not convo:
                raise HTTPException(404, "Conversation not found")

            if current_user.id not in {convo.buyer_id, convo.seller_id}:
                raise HTTPException(403, "Not allowed")

            if viewing_date <= datetime.now(timezone.utc):
                raise HTTPException(400, "Viewing date must be in the future")
            old_status = convo.viewing_status

            schedule_convo = await self.convos.set_viewing(
                convo=convo,
                viewing_date=viewing_date,
                status=ViewingStatus.PENDING,
            )
            await self.logs.log_viewing_change(
                convo_id=convo.id,
                old_status=old_status,
                new_status=schedule_convo.viewing_status,
                user_id=current_user.id,
            )

            return self.mapper.one(item=convo, schema=SaleConversationOut)

        return await self.breaker.call(handler)

    async def _respond_to_viewing(
        self,
        convo_id: UUID,
        current_user,
        response: ViewingStatus,
    ):
        async def handler():
            convo = await self.convos.get_conversation_by_id(convo_id)

            if not convo:
                raise HTTPException(404)

            if current_user.id not in {convo.buyer_id, convo.seller_id}:
                raise HTTPException(403)
            if convo.last_viewing_set_by == current_user.id:
                raise HTTPException(
                    400, "You cannot respond to your own viewing request"
                )

            if convo.viewing_status != ViewingStatus.PENDING:
                raise HTTPException(400, "Viewing already responded to")
            old_status = convo.viewing_status

            convo_response = await self.convos.set_viewing(
                convo=convo, status=response, viewing_date=convo.viewing_date
            )
            await self.logs.log_viewing_change(
                convo_id=convo.id,
                old_status=old_status,
                new_status=convo_response.viewing_status,
                user_id=current_user.id,
            )

            return self.mapper.one(item=convo, schema=SaleConversationOut)

        return await self.breaker.call(handler)

    async def cancel_viewing(self, convo_id: UUID, current_user):
        async def handler():
            convo = await self.convos.get_conversation_by_id(convo_id)

            if not convo:
                raise HTTPException(404)

            if current_user.id not in {convo.buyer_id, convo.seller_id}:
                raise HTTPException(403)
            old_status = convo.viewing_status

            cancel_convo = await self.convos.set_viewing(
                convo=convo,
                viewing_date=None,
                status=ViewingStatus.CANCELLED,
            )
            await self.logs.log_viewing_change(
                convo_id=convo.id,
                old_status=old_status,
                new_status=cancel_convo.viewing_status,
                user_id=current_user.id,
            )

            return self.mapper.one(item=convo, schema=SaleConversationOut)

        return await self.breaker.call(handler)

    async def approve_viewing(self, convo_id: UUID, current_user):
        return await self._respond_to_viewing(
            convo_id, current_user, ViewingStatus.APPROVED
        )

    async def decline_viewing(self, convo_id: UUID, current_user):
        return await self._respond_to_viewing(
            convo_id, current_user, ViewingStatus.DECLINED
        )

    async def list_messages(
        self, current_user, conversation_id: UUID, page: int = 1, per_page: int = 20
    ):
        async def handler():
            convo = await self.convos.get_conversation_by_id(conversation_id)
            if not convo:
                raise HTTPException(404, "Conversation not found")
            cache_key = f"sale_messages:{conversation_id}:{current_user.id}"
            cached = await self.cache.get_json(cache_key)
            if cached:
                return cached

            if current_user.id not in (convo.buyer_id, convo.seller_id):
                raise PermissionError("Not a participant")

            messages = await self.messages.list_for_conversation_for_user(
                conversation_id,
                current_user.id,
            )
            message_dicts = self.mapper.many(items=messages, schema=MessageOut)
            paginated_files = self.paginate.paginate(message_dicts, page, per_page)
            await self.cache.set_json(
                cache_key,
                self.paginate.get_list_json_dumps(paginated_files),
                ttl=300,
            )
            return paginated_files

        return await self.breaker.call(handler)

    async def list_messages_for_cursor(
        self,
        current_user,
        conversation_id: UUID,
        limit: int = 20,
        before: datetime | None = None,
    ):
        async def handler():
            convo = await self.convos.get_conversation_by_id(conversation_id)
            if not convo:
                raise HTTPException(404, "Conversation not found")

            if current_user.id not in (convo.buyer_id, convo.seller_id):
                raise PermissionError("Not a participant")
            cached = None
            if not before:
                cache_key = (
                    f"sale_messages:latest:cursor:{conversation_id}:{current_user.id}"
                )
                cached = await self.cache.get_json(cache_key)
            if cached:
                return cached

            (
                messages,
                next_cursor,
            ) = await self.messages.list_for_conversation_for_user_cursor(
                conversation_id=conversation_id,
                user_id=current_user.id,
                limit=limit,
                before=before,
            )
            await self.messages.mark_conversation_as_read(
                conversation_id, current_user.id
            )
            items = self.mapper.many(messages, MessageCursorOut)
            page = CursorPage.model_validate(
                {"items": items, "next_cursor": next_cursor}
            )
            if not before:
                await self.cache.set_json(
                    cache_key, page.model_dump(mode="json"), ttl=300
                )
            return page

        return await self.breaker.call(handler)

    async def start_or_get_conversation(self, current_user, listing_id: UUID):
        async def handler():
            listing = await self.listings.get_listing_id(listing_id)

            if not listing:
                raise HTTPException(404, "Listing not found")

            if listing.listed_by_id == current_user.id:
                raise HTTPException(400, "You cannot message yourself")
            if not listing.is_available:
                raise HTTPException(400, "This property has been sold")

            convo = await self.convos.get_or_create(
                buyer_id=current_user.id,
                listing=listing,
            )

            return self.mapper.one(item=convo, schema=SaleConversationOut)

        return await self.breaker.call(handler)

    async def send_message(
        self,
        *,
        current_user,
        payload,
        conversation_id: UUID,
    ):
        async def handler():
            conversation = await self.convos.get_conversation_by_id(conversation_id)

            if not conversation:
                raise HTTPException(404, "Conversation not found")

            if current_user.id not in (
                conversation.buyer_id,
                conversation.seller_id,
            ):
                raise HTTPException(403, "Not part of this conversation")

            receiver_id = (
                conversation.seller_id
                if current_user.id == conversation.buyer_id
                else conversation.buyer_id
            )

            msg = await self.messages.create(
                conversation_id=conversation.id,
                sender_id=current_user.id,
                receiver_id=receiver_id,
                ciphertext=payload.ciphertext,
                nonce=payload.nonce,
                sender_public_key=payload.sender_public_key,
            )

            return self.mapper.one(item=msg, schema=EncryptedMessageOut)

        return await self.breaker.call(handler)

    async def hard_delete_message(
        self,
        conversation_id: UUID,
        current_user,
    ):
        async def handler():
            conversation = await self.convos.get_conversation_by_id(conversation_id)

            if not conversation:
                raise HTTPException(404, "Conversation not found")

            if current_user.id not in (
                conversation.buyer_id,
                conversation.seller_id,
            ):
                raise HTTPException(403, "Not part of this conversation")

            await self.convos.hard_delete_conversation(conversation_id)

            return {"detail": "Conversation deleted"}

        return await self.breaker.call(handler)

    async def soft_delete_message(self, message_id: UUID, current_user):
        async def handler():
            msg = await self.messages.soft_delete_for_user(
                message_id,
                current_user.id,
            )
            if not msg:
                raise ValueError("Message not found")
            return msg

        return await self.breaker.call(handler)
