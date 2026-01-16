from core.cloudinary_setup import cloudinary_client
from core.get_current_user import get_current_user
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends, Query
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import (
    MultiUploadRequest,
    UploadDeleteRequest,
    UploadSingleDeleteRequest,
)
from typing import List

router = APIRouter(tags=["Cloudinary Signature Params Route"])


@cbv(router)
class CloudinaryRoutes:
    @router.get("/cloudinary/image/signature", dependencies=[rate_limit])
    @safe_handler
    async def get_image_signature(
        self,
        _: None = Depends(validate_csrf_dependency),
    ):
        return await cloudinary_client.get_image_signed_upload_params()

    @router.get("/cloudinary/video/signature", dependencies=[rate_limit])
    @safe_handler
    async def get_video_signature(
        self,
        _: None = Depends(validate_csrf_dependency),
    ):
        return await cloudinary_client.get_signed_video_upload_params()

    @router.post("/cloudinary/multiple/image/signature", dependencies=[rate_limit])
    @safe_handler
    async def get_multiple_image_signatures(
        self,
        payload: MultiUploadRequest,
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await cloudinary_client.get_signed_multiple_upload_params(
            count=payload.count,
            folder=f"uploads/{current_user.id}",
        )

    @router.get("/cloudinary/pdf/signature", dependencies=[rate_limit])
    @safe_handler
    async def get_pdf_signed_upload_params(
        self,
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await cloudinary_client.get_pdf_signed_upload_params()

    @router.post("/cloudinary/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete(
        self,
        data: UploadSingleDeleteRequest,
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await cloudinary_client.delete_image(
            public_id=data.public_id, resource_type=data.resource_type
        )

    @router.post("/cloudinary/delete/multiple", dependencies=[rate_limit])
    @safe_handler
    async def delete_multiple(
        self,
        data: UploadDeleteRequest,
        current_user: User = Depends(get_current_user),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await cloudinary_client.delete_images(
            public_ids=data.public_ids, resource_type=data.resource_type
        )

    @router.get("/cloudinary/resources", dependencies=[rate_limit])
    @safe_handler
    async def list_cloudinary_resources(
        self,
        resource_type: str = Query("image", regex="^(image|video|raw)$"),
        folder: str | None = None,
        max_results: int = 50,
        next_cursor: str | None = None,
        current_user: User = Depends(get_current_user),
    ):
        # 🔐 enforce admin access
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")

        return await cloudinary_client.list_resources(
            resource_type=resource_type,
            folder=folder,
            max_results=max_results,
            next_cursor=next_cursor,
        )
