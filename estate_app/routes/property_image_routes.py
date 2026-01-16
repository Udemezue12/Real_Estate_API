import uuid

from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import CloudinaryUpdateRequest, CloudinaryUploadRequest
from services.property_image_service import PropertyImageService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Upload Images"])


@cbv(router)
class PropertyUploadImageRoutes:
    @router.get("/{property_id}/get", dependencies=[rate_limit])
    @safe_handler
    async def get(
        self,
        property_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyImageService(db).get_all_images(property_id=property_id)

    @router.post("/{property_id}/upload", dependencies=[rate_limit])
    @safe_handler
    async def upload(
        self,
        property_id: uuid.UUID,
        data: CloudinaryUploadRequest,
        db: AsyncSession = Depends(get_db_async),
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyImageService(db).upload_image(
            property_id=property_id,
            image_url=data.secure_url,
            public_id=data.public_id,
            current_user=current_user,
        )

    @router.post("/{image_id}/update", dependencies=[rate_limit])
    @safe_handler
    async def update_image(
        self,
        image_id: uuid.UUID,
        payload: CloudinaryUpdateRequest,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PropertyImageService(db).update_image(
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
        return await PropertyImageService(db).delete_image(
            image_id=image_id, current_user=current_user
        )
