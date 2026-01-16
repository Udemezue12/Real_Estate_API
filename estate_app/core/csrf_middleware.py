from datetime import datetime, timedelta, timezone
from typing import Set

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class AutoRefreshAccessTokenMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        secret_key: str,
        algorithm: str = "HS256",
        access_exp_minutes: int = 10,
        secure_cookies: bool = True,
        skip_paths: Set[str] = None,
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_exp = timedelta(minutes=access_exp_minutes)
        self.secure_cookies = secure_cookies
        self.skip_paths = skip_paths or {"/logout", "/api/auth/logout"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.skip_paths:
            return await call_next(request)

        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        if access_token:
            new_access = self._try_refresh_access_token(access_token)
            if new_access:
                response = await call_next(request)
                self._set_access_cookie(response, new_access)
                return response

        if refresh_token:
            new_access = self._try_create_access_from_refresh(refresh_token)
            if new_access:
                response = await call_next(request)
                self._set_access_cookie(response, new_access)
                return response
            else:
                # if request.url.path.startswith("/api/"):
                resp = JSONResponse(
                    {"detail": "Refresh token expired"}, status_code=401
                )
                resp.delete_cookie("refresh_token")
                return resp

        response = await call_next(request)
        return response

    def _try_refresh_access_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

            if exp - datetime.now(timezone.utc) < timedelta(minutes=2):
                return self._create_new_access_token(payload["sub"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
        return None

    def _try_create_access_from_refresh(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return self._create_new_access_token(payload["sub"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    def _create_new_access_token(self, user_id) -> str:
        return jwt.encode(
            {
                "sub": user_id,
                "type": "access",
                "exp": datetime.now(timezone.utc) + self.access_exp,
            },
            self.secret_key,
            algorithm=self.algorithm,
        )

    def _set_access_cookie(self, response: Response, token: str):
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=self.secure_cookies,
            samesite="lax",
            max_age=int(self.access_exp.total_seconds()),
        )
