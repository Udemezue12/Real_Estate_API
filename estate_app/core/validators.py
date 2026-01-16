import uuid

import jwt
from jose import jwt as websocket_jwt, JWTError
from fastapi import HTTPException, Request, status, WebSocket

from .settings import settings


def decode_ws_access_token(token: str) -> uuid.UUID:
    try:
        payload = websocket_jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token missing user ID")

        return uuid.UUID(user_id)

    except JWTError:
        raise ValueError("Invalid or expired token")


def decode_http_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token missing user ID")

        return uuid.UUID(user_id)

    except JWTError:
        raise ValueError("Invalid or expired token")


async def validate_csrf(request: Request):
    try:
        session_token = request.session.get("csrf_token")
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf_token")

        if not (session_token and cookie_token):
            # if not (session_token and cookie_token and header_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token"
            )

        # Compare header vs cookie
        # if header_token != cookie_token:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="CSRF token mismatch (header vs cookie)",
        #     )

        if session_token != cookie_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token: mismatch with session token.",
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSRF validation failed: {str(e)}")


async def validate_csrf_ws(websocket: WebSocket):
    cookie_token = websocket.cookies.get("csrf_token")
    query_token = websocket.query_params.get("csrf")

    if not cookie_token or not query_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    if cookie_token != query_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    return True


async def validate_csrf_dependency(request: Request):
    try:
        if any(
            path in str(request.url) for path in ["/docs", "/openapi.json", "/redoc"]
        ):
            return
        await validate_csrf(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def validate_csrf_dependency_ws(websocket: WebSocket):
    try:
        if any(
            path in str(websocket.url) for path in ["/docs", "/openapi.json", "/redoc"]
        ):
            return
        await validate_csrf_ws(websocket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def jwt_protect(request: Request) -> uuid.UUID:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        return decode_http_access_token(token)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def passkey_jwt_protect(request: Request) -> uuid.UUID:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_http_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
