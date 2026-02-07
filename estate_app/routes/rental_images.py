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
    BaseImageOut,
    CloudinaryUpdateRequest,
    CloudinaryUploadRequest,
)
from services.rental_images_service import RentalListingImageService

router = APIRouter(tags=["Upload Images"])


@cbv(router)
class RentalUploadImageRoutes:
    @router.get(
        "/{rental_listing_id}/get",
        dependencies=[rate_limit],
        response_model=list[BaseImageOut],
    )
    @safe_handler
    async def get(
        self,
        rental_listing_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalListingImageService(db).get_all_images(
            listing_id=rental_listing_id, page=page, per_page=per_page
        )

    @router.post("/{rental_listing_id}/upload")
    @safe_handler
    async def upload(
        self,
        rental_listing_id: uuid.UUID,
        data: CloudinaryUploadRequest,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalListingImageService(db).upload_image(
            listing_id=rental_listing_id,
            image_url=data.secure_url,
            public_id=data.public_id,
            current_user=current_user,
        )

    @router.post("{image_id}/update", dependencies=[rate_limit])
    @safe_handler
    async def update_image(
        self,
        image_id: uuid.UUID,
        payload: CloudinaryUpdateRequest,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalListingImageService(db).update_image(
            image_id=image_id,
            secure_url=payload.secure_url,
            public_id=payload.public_id,
            current_user=current_user,
        )

    @router.delete("{image_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete_image(
        self,
        image_id: uuid.UUID,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await RentalListingImageService(db).delete_image(
            image_id=image_id,
            current_user=current_user,
        )
