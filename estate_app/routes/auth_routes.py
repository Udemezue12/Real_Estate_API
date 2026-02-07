from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from core.check_login import check_logged_in, check_not_logged_in
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from schemas.schema import (
    ForgotPasswordSchema,
    ResendEmailSchema,
    ResetPasswordSchema,
    UserCreate,
    UserLoginInput,
)
from security.security_verification import UserVerification
from services.auth_service import AuthService

router = APIRouter(tags=["User Authentication"])


@cbv(router)
class UserRoutes:
    @router.post(
        "/register",
        dependencies=[
            rate_limit,
            Depends(check_not_logged_in),
        ],
    )
    @safe_handler
    async def register(
        self,
        data: UserCreate,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await AuthService(db).register(data, background_tasks)

    @router.post("/login", dependencies=[rate_limit])
    @safe_handler
    async def login(
        self,
        data: UserLoginInput,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await AuthService(db).login(data)

    @router.post(
        "/logout",
        dependencies=[rate_limit, Depends(check_logged_in)],
    )
    @safe_handler
    async def logout(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await AuthService(db).logout(request)

    @router.post(
        "/refresh",
        dependencies=[rate_limit],
    )
    @safe_handler
    async def refresh(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await AuthService(db).refresh(request)

    @router.post("/verify-email", dependencies=[rate_limit])
    @safe_handler
    async def verify_email(
        self,
        otp: str | None = None,
        token: str | None = None,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserVerification(db).verify_email(otp, token)

    @router.post("/resend-verification-link", dependencies=[rate_limit])
    @safe_handler
    async def resend_verification_link(
        self,
        payload: ResendEmailSchema,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserVerification(db).resend_verification_email(
            email=payload.email, background_tasks=background_tasks
        )

    @router.post("/resend-password-reset-link", dependencies=[rate_limit])
    @safe_handler
    async def resend_password_reset_link(
        self,
        payload: ResendEmailSchema,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await UserVerification(db).resend_password_reset_link(
            email=payload.email, background_tasks=background_tasks
        )

    @router.post("/forgot-password", dependencies=[rate_limit])
    @safe_handler
    async def forgot_password(
        self,
        payload: ForgotPasswordSchema,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await AuthService(db).forgot_password(payload, background_tasks)

    @router.post("/reset-password", dependencies=[rate_limit])
    @safe_handler
    async def reset_password(
        self,
        payload: ResetPasswordSchema,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await AuthService(db).reset_password(payload)
