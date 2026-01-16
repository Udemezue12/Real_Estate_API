import uuid

from core.get_current_user import passkey_get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import (
    CredentialAttestationOut,
)
from services.passkey_service import PasskeyService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Passkey Authentication"])


@cbv(router)
class PasskeyRoutes:
    @router.post("/start/register", dependencies=[rate_limit])
    @safe_handler
    async def start_register(
        self,
        current_user: User = Depends(passkey_get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).start_passkey_registration(
            current_user=current_user
        )

    @router.post("/complete/register", dependencies=[rate_limit])
    @safe_handler
    async def complete_register(
        self,
        registration_response: dict,
        current_user: User = Depends(passkey_get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).complete_passkey_registration(
            current_user=current_user, registration_response=registration_response
        )

    @router.post("/authenticate", dependencies=[rate_limit])
    @safe_handler
    async def authenticate(
        self,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).start_passkey_login()

    @router.get("/verify", dependencies=[rate_limit])
    @safe_handler
    async def verify(
        self,
        assertion: dict,
        current_user: User = Depends(passkey_get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).verify_passkey_login(assertion=assertion)

    @router.get("/devices", dependencies=[rate_limit])
    @safe_handler
    async def get_registered_passkey(
        self,
        current_user: User = Depends(passkey_get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).get_registered_passkeys(user_id=current_user.id)

    @router.get(
        "/passkeys",
        dependencies=[rate_limit],
        response_model=list[CredentialAttestationOut],
    )
    @safe_handler
    async def all_passkeys(
        self,
        page: int = 1,
        per_page: int = 20,
        current_user: User = Depends(passkey_get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).get_passkeys(
            current_user=current_user, page=page, per_page=per_page
        )

    @router.get("/{passkey_id}/get", dependencies=[rate_limit])
    @safe_handler
    async def get_passkey(
        self,
        passkey_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(passkey_get_current_user),
    ):
        return await PasskeyService(db).get_passkey_by_id(
            passkey_id=passkey_id, current_user=current_user
        )

    @router.delete("/{passkey_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete(
        self,
        passkey_id: uuid.UUID,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await PasskeyService(db).delete(passkey_id=passkey_id)
