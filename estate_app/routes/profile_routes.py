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
    ReVerifyAccountNumber,
    ReVerifyBVN,
    ReVerifyNin,
    UserProfileSchema,
    UserProfileSchemaOut,
    UserProfileUpdateSchema,
)
from security.security_verification import UserVerification
from services.profile_service import UserProfileService

router = APIRouter(tags=["User Profile"])


@cbv(router)
class UserProfileRoutes:
    @router.get(
        "/{profile_id}",
        dependencies=[rate_limit],
        response_model=UserProfileSchemaOut,
    )
    @safe_handler
    async def get(
        self,
        profile_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserProfileService(db).get(
            current_user=current_user, profile_id=profile_id
        )

    @router.post(
        "/create", dependencies=[rate_limit], response_model=UserProfileSchemaOut
    )
    @safe_handler
    async def create(
        self,
        data: UserProfileSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserProfileService(db).create(data=data, current_user=current_user)

    @router.patch(
        "/{profile_id}/update",
        dependencies=[rate_limit],
        response_model=UserProfileSchemaOut,
    )
    @safe_handler
    async def update(
        self,
        profile_id: uuid.UUID,
        data: UserProfileUpdateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserProfileService(db).update(
            current_user=current_user, profile_id=profile_id, data=data
        )

    @router.delete(
        "/{profile_id}/delete",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def delete(
        self,
        profile_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserProfileService(db).delete(
            current_user=current_user,
            profile_id=profile_id,
        )

    @router.post(
        "/{profile_id}/reverify/nin",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def reverify_nin(
        self,
        profile_id: uuid.UUID,
        data: ReVerifyNin,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserVerification(db).reverify_nin(data=data, profile_id=profile_id)

    @router.post(
        "/{profile_id}/reverify/bvn",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def reverify_bvn(
        self,
        profile_id: uuid.UUID,
        data: ReVerifyBVN,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserVerification(db).reverify_bvn(data=data, profile_id=profile_id)

    @router.post(
        "/{profile_id}/reverify/account_number",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def reverify_account_number(
        self,
        profile_id: uuid.UUID,
        data: ReVerifyAccountNumber,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserVerification(db).reverify_account_number(
            data=data, profile_id=profile_id
        )
