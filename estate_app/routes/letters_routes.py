import uuid

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
    LetterRecipientOut,
    LetterSchemaOut,
    LetterUploadWithoutPDFSchema,
    LetterUploadWithPDFSchema,
)
from services.letter_service import LetterService

router = APIRouter(tags=["Send and View Official Letters"])


@cbv(router=router)
class LettersRoutes:
    @router.post("/{property_id}/{tenant_id}/send", dependencies=[rate_limit])
    @safe_handler
    async def send_without_pdf(
        self,
        property_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: LetterUploadWithoutPDFSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).send_letter_without_pdf_upload(
            data=data,
            current_user=current_user,
            tenant_id=tenant_id,
            property_id=property_id,
        )

    @router.post("/{property_id}/send/bulk", dependencies=[rate_limit])
    @safe_handler
    async def bulk_send_without_pdf(
        self,
        property_id: uuid.UUID,
        data: LetterUploadWithoutPDFSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).send_bulk_letters_without_pdf(
            data=data,
            current_user=current_user,
            property_id=property_id
        )

    @router.post("/{property_id}/{tenant_id}/upload/send", dependencies=[rate_limit])
    @safe_handler
    async def send_with_pdf(
        self,
        property_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: LetterUploadWithPDFSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).send_letter_with_pdf(
            data=data,
            current_user=current_user,
            tenant_id=tenant_id,
            property_id=property_id,
        )

    @router.post("/{property_id}/upload/send/bulk", dependencies=[rate_limit])
    @safe_handler
    async def bulk_send_with_pdf(
        self,
        property_id: uuid.UUID,
        data: LetterUploadWithPDFSchema,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).send_bulk_letters_with_pdf(
            data=data,
            current_user=current_user,
            property_id=property_id
        )

    @router.get(
        "/get/landlord", dependencies=[rate_limit], response_model=list[LetterSchemaOut]
    )
    @safe_handler
    async def get_all_letters_for_landlord(
        self,
        page: int = 1,
        per_page=20,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).get_all_letters_for_landlord(
            current_user=current_user, page=page, per_page=per_page
        )

    @router.get(
        "/get/{property_id}/landlord",
        dependencies=[rate_limit],
        response_model=list[LetterSchemaOut],
    )
    @safe_handler
    async def get_all_properties_letters(
        self,
        property_id: uuid.UUID,
        page: int = 1,
        per_page=20,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).get_all_properties_letters(
            current_user=current_user,
            page=page,
            per_page=per_page,
            property_id=property_id,
        )

    @router.get(
        "/get/{letter_id}/landlord",
        dependencies=[rate_limit],
        response_model=LetterSchemaOut,
    )
    @safe_handler
    async def get_single_letter_landlord(
        self,
        letter_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).get_single_letter_landlord(
            current_user=current_user,
            letter_id=letter_id,
        )

    @router.get(
        "/get/{property_id}/{letter_id}/landlord",
        dependencies=[rate_limit],
        response_model=LetterSchemaOut,
    )
    @safe_handler
    async def get_single_property_letter(
        self,
        letter_id: uuid.UUID,
        property_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).get_single_property_letter(
            current_user=current_user, letter_id=letter_id, property_id=property_id
        )

    @router.get(
        "/get/{letter_id}/tenant",
        dependencies=[rate_limit],
        response_model=LetterRecipientOut,
    )
    @safe_handler
    async def get_single_letter_for_tenant(
        self,
        recipient_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).get_single_letter_for_tenant(
            current_user=current_user, recipient_id=recipient_id
        )

    @router.get(
        "/get/tenant/all",
        dependencies=[rate_limit],
        response_model=list[LetterRecipientOut],
    )
    @safe_handler
    async def get_all_tenant_letters(
        self,
        page: int = 1,
        per_page=20,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await LetterService(db).get_all_tenant_letters(
            current_user=current_user, page=page, per_page=per_page
        )
