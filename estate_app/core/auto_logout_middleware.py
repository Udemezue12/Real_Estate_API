from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError, jwt
from repos.auth_repo import AuthRepo
from starlette.middleware.base import BaseHTTPMiddleware

from core.cache import cache
from core.get_db import AsyncSessionLocal
from core.settings import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
AUTO_LOGOUT_SECONDS = 10 * 60


class AutoLogoutMiddleware(BaseHTTPMiddleware):

    @classmethod
    async def _logout_response(cls) -> JSONResponse:
        response = JSONResponse(
            {"detail": "Session expired due to inactivity"},
            status_code=401,
        )

        for cookie in (
            "access_token",
            "refresh_token",
            "csrf_token",
            "session",
        ):
            response.delete_cookie(
                key=cookie,
                path="/",
                httponly=True,
                samesite="lax",
                secure=settings.SECURE_COOKIES,
            )

        return response

    @classmethod
    async def _decode_access_user_id(cls, token: str) -> str | None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload.get("sub")
        except (JWTError, ExpiredSignatureError):
            return None

    async def _blacklist_tokens(self, access_token: str, refresh_token: str | None):
        async with AsyncSessionLocal() as db:
            repo = AuthRepo(db)
            await repo.blacklist_token(access_token)
            if refresh_token:
                await repo.blacklist_token(refresh_token)

    async def dispatch(self, request: Request, call_next):
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        if not access_token:
            return await call_next(request)

        user_id = await self._decode_access_user_id(access_token)
        if not user_id:
            await self._blacklist_tokens(access_token, refresh_token)
            return await self._logout_response()

        redis_key = f"auth:last_activity:{user_id}"
        now = int(datetime.now(timezone.utc).timestamp())

        last_activity = await cache.get(redis_key)

        if last_activity:
            inactivity = now - int(last_activity)
            if inactivity > AUTO_LOGOUT_SECONDS:
                await self._blacklist_tokens(access_token, refresh_token)
                await cache.delete(redis_key)
                return await self._logout_response()

        
        await cache.set(
            redis_key,
            str(now),
            ttl=AUTO_LOGOUT_SECONDS,
        )

        return await call_next(request)
