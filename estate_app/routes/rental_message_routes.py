import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from models.models import User
from schemas.schema import (
    EncryptedMessageCreate,
    EncryptedMessageOut,
    RentalConversationOut,
    ScheduleViewingIn,
)
from services.rental_message_service import RentalMessagingService

router = APIRouter(tags=["Property Listing For Rent Messaging "])


@cbv(router)
class RentalMessageRoutes:
    @router.patch(
        "/conversations/{convo_id}/viewing/schedule",
        response_model=RentalConversationOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def schedule_viewing(
        self,
        convo_id: uuid.UUID,
        payload: ScheduleViewingIn,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalMessagingService(db).schedule_viewing(
            convo_id=convo_id,
            viewing_date=payload.viewing_date,
            current_user=current_user,
        )

    @router.delete(
        "/conversations/{convo_id}/viewing/delete",
        response_model=RentalConversationOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def delete_viewing(
        self,
        convo_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalMessagingService(db).cancel_viewing(
            convo_id=convo_id,
            current_user=current_user,
        )

    @router.post(
        "/conversations/{convo_id}/viewing/approve",
        response_model=RentalConversationOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def approve_viewing(
        self,
        convo_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalMessagingService(db).approve_viewing(convo_id=convo_id)

    @router.post(
        "/conversations/{convo_id}/viewing/decline",
        response_model=RentalConversationOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def decline_viewing(
        self,
        convo_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalMessagingService(db).decline_viewing(
            convo_id=convo_id,
        )

    @router.post(
        "/{listing_id}/start/conversations",
        response_model=RentalConversationOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def start_conversation(
        self,
        listing_id: str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
    ):
        return await RentalMessagingService(db).start_or_get_conversation(
            current_user=current_user, listing_id=listing_id
        )

    @router.post(
        "/conversations/{conversation_id}/messages",
        response_model=EncryptedMessageOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def send_message(
        self,
        conversation_id: uuid.UUID,
        payload: EncryptedMessageCreate,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
    ):
        return await RentalMessagingService(db).send_message(
            current_user=current_user, payload=payload, conversation_id=conversation_id
        )

    @router.get(
        "/{conversation_id}/messages",
        response_model=EncryptedMessageOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def list_messages(
        self,
        conversation_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
        page: int = 1,
        per_page: int = 20,
    ):
        return await RentalMessagingService(db).list_messages(
            current_user=current_user,
            conversation_id=conversation_id,
            page=page,
            per_page=per_page,
        )

    @router.get(
        "/{conversation_id}/cursor/messages",
        response_model=EncryptedMessageOut,
        dependencies=[rate_limit],
    )
    @safe_handler
    async def list_cursor_messages(
        self,
        conversation_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
        limit: int = 20,
        before: datetime | None = None,
    ):
        return await RentalMessagingService(db).list_messages_for_cursor(
            current_user=current_user,
            conversation_id=conversation_id,
            limit=limit,
            before=before,
        )

    @router.delete(
        "/{conversation_id}/delete/messages",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def hard_delete_message(
        self,
        conversation_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
    ):
        return await RentalMessagingService(db).hard_delete_message(
            current_user=current_user,
            conversation_id=conversation_id,
        )

    @router.delete(
        "/{message_id}/delete/soft/messages",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def soft_delete_message(
        self,
        message_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(get_current_user),
    ):
        return await RentalMessagingService(db).soft_delete_message(
            current_user=current_user, message_id=message_id
        )
